"""
Implements a simple service using cx_Freeze.

See below for more information on what methods must be implemented and how they
are called.
"""

import cx_Logging
import threading
import configparser
import glob
import logging
import logging.handlers
import os
import time
import sys
from gevent.pywsgi import WSGIServer
from gevent.pool import Pool
# DO NOT REMOVE THIS, THIS FORCES cx_Freeze to include the library
# DO NOT REMOVE ANYTHING BELOW THIS LINE
import passive.nrds
import passive.nrdp
import listener.server
import listener.psapi
import listener.windowscounters
import listener.windowslogs
import listener.certificate
import jinja2.ext
import webhandler
import filename
import ssl
import gevent.builtins
from gevent import monkey

monkey.patch_all(subprocess=True, thread=False)

class Base(object):
    # no parameters are permitted; all configuration should be placed in the
    # configuration file and handled in the Initialize() method
    def __init__(self, debug=False):
        logging.getLogger().handlers = []
        self.stopEvent = threading.Event()
        self.debug = debug

    def determine_relative_filename(self, file_name, *args, **kwargs):
        """Gets the relative pathname of the executable being run.

        This is meant exclusively for being used with cx_Freeze on Windows.
        """
        if self.debug:
            appdir = os.path.dirname(filename.__file__)
        else:
            appdir = os.path.dirname(sys.path[0])

        # There is something wonky about Windows and its need for paths and how Python
        # pulls the above appdir, which doesn't come out absolute when the application
        # is frozen. Figured being absolutely sure its an absolute path here.
        return os.path.abspath(os.path.join(appdir, file_name))

    def parse_config(self, *args, **kwargs):
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.config.read(self.config_filenames)

    def setup_plugins(self):
        plugin_path = self.config.get('plugin directives', 'plugin_path')
        abs_plugin_path = self.determine_relative_filename(plugin_path)
        self.abs_plugin_path = os.path.normpath(abs_plugin_path)
        self.config.set('plugin directives', 'plugin_path', self.abs_plugin_path)

    def setup_logging(self, *args, **kwargs):
        """This should always setup the logger.

        """
        config = dict(self.config.items(self.c_type, 1))

        # Now we grab the logging specific items
        log_file = os.path.normpath(config['logfile'])
        if not os.path.isabs(log_file):
            log_file = self.determine_relative_filename(log_file)

        logging.getLogger().handlers = []

        # Max size of log files will be 20MB, and we'll keep one of them as backup
        max_log_size_bytes = int(config.get('logmaxmb', 5))
        max_log_rollovers = int(config.get('logbackups', 5))
        max_file_size = max_log_size_bytes * 1024 * 1024
        file_handler = logging.handlers.RotatingFileHandler(log_file,
                                                            maxBytes=max_file_size,
                                                            backupCount=max_log_rollovers)
        file_format = logging.Formatter('%(asctime)s:%(levelname)s:%(module)s:%(message)s')
        file_handler.setFormatter(file_format)

        logging.getLogger().addHandler(file_handler)

        # Set log level
        log_level_str = config.get('loglevel', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logging.getLogger().setLevel(log_level)

    # called when the service is starting immediately after Initialize()
    # use this to perform the work of the service; don't forget to set or check
    # for the stop event or the service GUI will not respond to requests to
    # stop the service
    def Run(self):
        self.start()
        self.stopEvent.Wait()

    # called when the service is being stopped by the service manager GUI
    def Stop(self):
        pass
        self.stopEvent.Set()


class Listener(Base):

    def start(self):

        # Check if there is a start delay
        try:
            delay_start = self.config.get('listener', 'delay_start')
            if delay_start:
                logging.info('Delayed start in configuration. Waiting %s seconds to start.', delay_start)
                time.sleep(int(delay_start))
        except Exception:
            pass

        try:

            address = self.config.get('listener', 'ip')
            port = self.config.getint('listener', 'port')
            listener.server.listener.config_files = self.config_filenames
            listener.server.listener.tail_method = listener.windowslogs.tail_method
            listener.server.listener.config['iconfig'] = self.config

            ssl_str_version = self.config.get('listener', 'ssl_version', fallback='TLSv1')

            try:
                ssl_version = getattr(ssl, 'PROTOCOL_' + ssl_str_version)
            except:
                ssl_version = getattr(ssl, 'PROTOCOL_TLSv1')
                ssl_str_version = 'TLSv1'

            logging.info('Using SSL version %s', ssl_str_version)

            user_cert = self.config.get('listener', 'certificate')

            if user_cert == 'adhoc':
                basepath = self.determine_relative_filename('')
                cert, key = listener.certificate.create_self_signed_cert(basepath, 'ncpa.crt', 'ncpa.key')
            else:
                cert, key = user_cert.split(',')
            ssl_context = {
                'certfile': cert,
                'keyfile': key,
                'ssl_version': ssl_version
            }

            listener.server.listener.secret_key = os.urandom(24)
            http_server = WSGIServer(listener=(address, port),
                                     application=listener.server.listener,
                                     handler_class=webhandler.PatchedWSGIHandler,
                                     spawn=Pool(200),
                                     **ssl_context)
            http_server.serve_forever()
        except Exception as e:
            logging.exception(e)

    # called when the service is starting
    def Initialize(self, config_file):
        self.c_type = 'listener'
        self.config_filenames = [self.determine_relative_filename(os.path.join('etc', 'ncpa.cfg'))]
        self.config_filenames.extend(sorted(glob.glob(self.determine_relative_filename(os.path.join(
            'etc', 'ncpa.cfg.d', '*.cfg')))))
        self.parse_config()
        self.setup_logging()
        self.setup_plugins()
        logging.info("Parsed config from: %s" % str(self.config_filenames))
        logging.info("Looking for plugins at: %s" % self.abs_plugin_path)


class Passive(Base):

    def run_all_handlers(self, *args, **kwargs):
        """Will run all handlers that exist.

        The handler must:
        - Have a config header entry
        - Abide by the handler API set forth by passive.abstract.NagiosHandler
        - Terminate in a timely fashion
        """
        handlers = self.config.get('passive', 'handlers').split(',')

        # Empty passive handlers will skip trying to run any handlers
        if handlers[0] == 'None' or handlers[0] == '':
            return

        # Runs either nrds or nrdp (or both)
        for handler in handlers:
            try:
                module_name = 'passive.%s' % handler
                __import__(module_name)
                tmp_handler = sys.modules[module_name]
            except ImportError as e:
                logging.error('Could not import module passive.%s, skipping. %s' % (handler, str(e)))
                logging.exception(e)
            else:
                try:
                    ins_handler = tmp_handler.Handler(self.config)
                    ins_handler.run()
                    logging.debug('Successfully ran handler %s' % handler)
                except Exception as e:
                    logging.exception(e)

    # Actual method that loops doing passive checks forever, using the sleep
    # config setting to wait for the next time to run
    #
    #   Removed the "self.parse_config()" after the run_all_handlers
    #   ----------
    #   Prior to 2.0.0, the configuration could be changed without restarting
    #   the NCPA passive service which caused the plugins to fail to run
    #   after the first time it ran, re-loading the improper path that hadn't
    #   been updated. This really isn't necessary, and has been removed to
    #   preserve the config that was being ran from the start.
    # 
    def start(self):

        # Check if there is a start delay
        try:
            delay_start = self.config.get('passive', 'delay_start')
            if delay_start:
                logging.info('Delayed start in configuration. Waiting %s seconds to start.', delay_start)
                time.sleep(int(delay_start))
        except Exception:
            pass

        try:
            while True:
                self.run_all_handlers()
                wait_time = self.config.getint('passive', 'sleep')
                time.sleep(wait_time)
        except Exception as e:
            logging.exception(e)

    # Called when the service is starting to initiate variables required by the main
    # passive "run_all_handlers" method
    def Initialize(self, config_file):
        self.c_type = 'passive'
        self.config_filenames = [self.determine_relative_filename(os.path.join('etc', 'ncpa.cfg'))]
        self.config_filenames.extend(sorted(glob.glob(self.determine_relative_filename(os.path.join(
            'etc', 'ncpa.cfg.d', '*.cfg')))))
        self.parse_config()
        self.setup_logging()
        self.setup_plugins()
        logging.info("Parsed config from: %s" % str(self.config_filenames))
        logging.info("Looking for plugins at: %s" % self.config.get('plugin directives', 'plugin_path'))
