'''Collections of helper functions for Gradio user interface.'''

import os
import re
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def get_dialog_logger(name: str = 'dialog', clear: bool = True) -> logging.Logger:
    '''Sets up logger for model's internal dialog.'''

    # Make sure log directory exists
    Path('logs').mkdir(parents=True, exist_ok=True)

    # Clear old logs if desired
    if clear:
        delete_old_logs('logs', 'dialog')

    # Create logger
    new_dialog_logger = logging.getLogger(name)

    # Create handler
    handler = RotatingFileHandler(
        'logs/dialog.log',
        maxBytes=100000,
        backupCount=10,
        mode='w'
    )

    # Add format to handler
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    new_dialog_logger.addHandler(handler)

    # Set logging level
    new_dialog_logger.setLevel(logging.INFO)

    return new_dialog_logger


def update_dialog(n: int = 10):
    '''Gets updated internal dialog logging output from disk to display to user.
    
    Args:
        n: number of most recent lines of internal dialog output to display

    Returns:
        Internal dialog logging output as string
    '''

    with open('logs/dialog.log', 'r', encoding='utf-8') as log_file:
        lines = log_file.readlines()

    return ''.join(lines[-n:])


def delete_old_logs(directory:str, basename:str) -> None:
    '''Deletes old log files from previous optimization sessions, if present.
    
    Args:
        directory: path to log file directory as string
        basename: log file base name as string
        
    Returns:
        None
    '''

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if re.search(basename, filename):
            os.remove(file_path)
