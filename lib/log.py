#!/usr/bin/env python
"""Generic logging, the way I remember it from scripts gone by.

TODO:
- network logging support.
- ability to change log settings mid-stream
- per-module log settings
- are we really forced to use global logging.* settings???
  - i hope i'm mistaken here
  - would love to do instance-based settings so we can have multiple
    objects that can each have their own logger
- ability to queryConfig/queryVar from here
  - log rotation config
  - general "echo-don't-execute" flag that gets every destructive method in
    BasicFunctions to echo only
"""

from datetime import datetime
import logging
import os
import sys

# Define our own FATAL
FATAL = logging.CRITICAL + 10
logging.addLevelName(FATAL, 'FATAL')



# BaseLogger {{{1
class BaseLogger(object):
    """Create a base logging class.
    TODO: status? There may be a status object or status capability in
    either logging or config that allows you to count the number of
    error,critical,fatal messages for us to count up at the end (aiming
    for 0).

    This "warning" instead of "warn" is going to trip me up.
    (It has, already.)
    However, while adding a 'warn': logging.WARNING would be nice,

        a) I don't want to confuse people who know the logging module and
           are comfortable with WARNING, so removing 'warning' is out, and
        b) there's a |for level in self.LEVELS.keys():| below, which would
           create a dup .warn.log alongside the .warning.log.
    """
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL,
              'fatal': FATAL
             }

    def __init__(self, log_level='info',
                 log_format='%(message)s',
                 log_date_format='%H:%M:%S',
                 log_name='test',
                 log_to_console=True,
                 log_dir='.',
                 log_to_raw=False,
                 logger_name='',
                 halt_on_failure=True,
                 append_to_log=False,
                ):
        self.halt_on_failure = halt_on_failure,
        self.log_format = log_format
        self.log_date_format = log_date_format
        self.log_to_console = log_to_console
        self.log_to_raw = log_to_raw
        self.log_level = log_level
        self.log_name = log_name
        self.log_dir = log_dir
        self.append_to_log = append_to_log

        # Not sure what I'm going to use this for; useless unless we
        # can have multiple logging objects that don't trample each other
        self.logger_name = logger_name

        self.all_handlers = []
        self.log_files = {}

        self.createLogDir()

    def createLogDir(self):
        if os.path.exists(self.log_dir):
            if not os.path.isdir(self.log_dir):
                os.remove(self.log_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.abs_log_dir = os.path.abspath(self.log_dir)

    def initMessage(self, name=None):
        if not name:
            name = self.__class__.__name__
        self.info("%s online at %s in %s" % \
                  (name, datetime.now().strftime("%Y%m%d %H:%M:%S"),
                   os.getcwd()))

    def getLoggerLevel(self, level=None):
        if not level:
            level = self.log_level
        return self.LEVELS.get(level, logging.NOTSET)

    def getLogFormatter(self, log_format=None, date_format=None):
        if not log_format:
            log_format = self.log_format
        if not date_format:
            date_format = self.log_date_format
        return logging.Formatter(log_format, date_format)

    def newLogger(self, logger_name):
        """Create a new logger.
        By default there are no handlers.
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.getLoggerLevel())
        self._clearHandlers()
        if self.log_to_console:
            self.addConsoleHandler()
        if self.log_to_raw:
            self.log_files['raw'] = '%s_raw.log' % self.log_name
            self.addFileHandler(os.path.join(self.abs_log_dir,
                                             self.log_files['raw']),
                                log_format='%(message)s')

    def _clearHandlers(self):
        """To prevent dups -- logging will preserve Handlers across
        objects :(
        """
        attrs = dir(self)
        if 'all_handlers' in attrs and 'logger' in attrs:
            for handler in self.all_handlers:
                self.logger.removeHandler(handler)
            self.all_handlers = []

    def __del__(self):
        self._clearHandlers()

    def addConsoleHandler(self, log_level=None, log_format=None,
                          date_format=None):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.getLoggerLevel(log_level))
        console_handler.setFormatter(self.getLogFormatter(log_format=log_format,
                                                         date_format=date_format))
        self.logger.addHandler(console_handler)
        self.all_handlers.append(console_handler)

    def addFileHandler(self, log_path, log_level=None, log_format=None,
                       date_format=None):
        if not self.append_to_log and os.path.exists(log_path):
            os.remove(log_path)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(self.getLoggerLevel(log_level))
        file_handler.setFormatter(self.getLogFormatter(log_format=log_format,
                                                      date_format=date_format))
        self.logger.addHandler(file_handler)
        self.all_handlers.append(file_handler)

    def log(self, message, level='info', exit_code=-1):
        """Generic log method.
        There should be more options here -- do or don't split by line,
        use os.linesep instead of assuming \n, be able to pass in log level
        by name or number.

        Adding the "ignore" special level for runCommand.
        """
        if level == "ignore":
            return
        for line in message.splitlines():
            self.logger.log(self.getLoggerLevel(level), line)
        if level == 'fatal' and self.halt_on_failure:
            self.logger.log(FATAL, 'Exiting %d' % exit_code)
            sys.exit(exit_code)

    def debug(self, message):
        self.log(message, level='debug')

    def info(self, message):
        self.log(message, level='info')

    def warning(self, message):
        self.log(message, level='warning')

    def warn(self, message):
        self.log(message, level='warning')

    def error(self, message):
        self.log(message, level='error')

    def critical(self, message):
        self.log(message, level='critical')

    def fatal(self, message, exit_code=-1):
        self.log(message, level='fatal', exit_code=exit_code)


# SimpleFileLogger {{{1
class SimpleFileLogger(BaseLogger):
    """Create one logFile.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self,
                 log_format='%(asctime)s - %(levelname)7s - %(message)s',
                 logger_name='Simple', log_dir='logs', **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name, log_format=log_format,
                            log_dir=log_dir, **kwargs)
        self.newLogger(self.logger_name)
        self.initMessage()

    def newLogger(self, logger_name):
        BaseLogger.newLogger(self, logger_name)
        self.log_path = os.path.join(self.abs_log_dir, '%s.log' % self.log_name)
        self.log_files['default'] = self.log_path
        self.addFileHandler(self.log_path)




# MultiFileLogger {{{1
class MultiFileLogger(BaseLogger):
    """Create a log per log level in log_dir.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self, logger_name='Multi',
                 log_format='%(asctime)s - %(levelname)7s - %(message)s',
                 log_dir='logs', log_to_raw=True, **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name, log_format=log_format,
                            log_to_raw=log_to_raw, log_dir=log_dir,
                            **kwargs)

        self.newLogger(self.logger_name)
        self.initMessage()

    def newLogger(self, logger_name):
        BaseLogger.newLogger(self, logger_name)
        minLoggerLevel = self.getLoggerLevel(self.log_level)
        for level in self.LEVELS.keys():
            if self.getLoggerLevel(level) >= minLoggerLevel:
                self.log_files[level] = '%s_%s.log' % (self.log_name,
                                                      level)
                self.addFileHandler(os.path.join(self.abs_log_dir,
                                                 self.log_files[level]),
                                    log_level=level)



# __main__ {{{1

if __name__ == '__main__':
    """Quick 'n' dirty unit tests.
    Ideally, this would be parsed automatically, too, and wouldn't leave
    cruft behind.
    """
    def testLogger(obj):
        obj.log('YOU SHOULD NOT SEE THIS LINE', level='debug')
        for level in ('info', 'warning', 'error', 'critical'):
            obj.log('test %s' % level, level=level)
        try:
            obj.log('test fatal -- you should see an exit line after this.',
                    level='fatal')
        except:
            print "Yay, that's good."
        else:
            print "OH NO!"

    log_dir = 'test_logs'
    obj = MultiFileLogger(log_level='info', log_dir=log_dir,
                          log_to_raw=True)
    testLogger(obj)
    obj.halt_on_failure=False
    obj.log('test fatal -- you should *not* see an exit line after this.',
            level='fatal')
    obj = SimpleFileLogger(log_dir=log_dir)
    testLogger(obj)
    print "=========="
    print "You should be able to examine %s." % log_dir
