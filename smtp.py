"""
:author: Elizabeth Orwig

A simple email sending program.
"""

# GUI library for password entry
import tkinter as tk

# Socket library
import socket

# SSL/TLS library
import ssl

# base-64 encode/decode
import base64

# Python date/time and timezone modules
import datetime
import time
import pytz
import tzlocal
import hashlib

# Module for reading password from console without echoing it
import getpass

# Modules for some file operations
import os
import mimetypes

# Host name for MSOE (hosted) SMTP server
SMTP_SERVER = 'smtp.office365.com'

# The default port for STARTTLS SMTP servers is 587
SMTP_PORT = 587

# SMTP domain name
SMTP_DOMAINNAME = 'msoe.edu'


def main():
    """Main test method to send an SMTP email message.

    Modify data as needed/desired to test your code,
    but keep the same interface for the smtp_send
    method.
    """
    (username, password) = login_gui()

    message_info = {}
    message_info['To'] = '' #Add a valid .msoe email address!
    message_info['From'] = username
    message_info['Subject'] = 'A Message For You'
    message_info['Date'] = 'Thu, 9 Oct 2014 23:56:09 +0000'
    message_info['Date'] = get_formatted_date()

    print("message_info =", message_info)

    message_text = 'Test message_info number 6\r\n\r\nAnother line.'

    smtp_send(password, message_info, message_text)


def login_gui():
    """
    Creates a graphical user interface for secure user authorization.

    :return: (email_value, password_value)
        email_value -- The email address as a string.
        password_value -- The password as a string.

    """
    gui = tk.Tk()
    gui.title("MSOE Email Client")
    center_gui_on_screen(gui, 370, 120)

    tk.Label(gui, text="Please enter your MSOE credentials below:") \
        .grid(row=0, columnspan=2)
    tk.Label(gui, text="Email Address: ").grid(row=1)
    tk.Label(gui, text="Password:         ").grid(row=2)

    email = tk.StringVar()
    email_input = tk.Entry(gui, textvariable=email)
    email_input.grid(row=1, column=1)

    password = tk.StringVar()
    password_input = tk.Entry(gui, textvariable=password, show='*')
    password_input.grid(row=2, column=1)

    auth_button = tk.Button(gui, text="Authenticate", width=25, command=gui.destroy)
    auth_button.grid(row=3, column=1)

    gui.mainloop()

    email_value = email.get()
    password_value = password.get()

    return email_value, password_value


def center_gui_on_screen(gui, gui_width, gui_height):
    """Centers the graphical user interface on the screen.

    :param gui: The graphical user interface to be centered.
    :param gui_width: The width of the graphical user interface.
    :param gui_height: The height of the graphical user interface.
    :return: The graphical user interface coordinates for the center of the screen.
    """
    screen_width = gui.winfo_screenwidth()
    screen_height = gui.winfo_screenheight()
    x_coord = (screen_width / 2) - (gui_width / 2)
    y_coord = (screen_height / 2) - (gui_height / 2)

    return gui.geometry('%dx%d+%d+%d' % (gui_width, gui_height, x_coord, y_coord))

def smtp_send(password, message_info, message_text):
    """Send a message via SMTP.

    :param password: String containing user password.
    :param message_info: Dictionary with string values for the following keys:
                'To': Recipient address (only one recipient required)
                'From': Sender address
                'Date': Date string for current date/time in SMTP format
                'Subject': Email subject
            Other keys can be added to support other email headers, etc.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_address = (SMTP_SERVER, SMTP_PORT)
    server_socket.connect(listen_address)

    first_line = look_for_newline(server_socket)
    parse_and_send(first_line, b'2', b'2', b'0', "EHLO ".encode()+SMTP_DOMAINNAME.encode()+b"\r\n", server_socket)

    pass_in_to_parse_ehlo(server_socket)
    server_socket.send(b'STARTTLS\r\n')

    next_line = look_for_newline(server_socket)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(server_socket, server_hostname=SMTP_SERVER)

    parse_and_send(next_line, b'2', b'2', b'0', "EHLO ".encode()+SMTP_DOMAINNAME.encode()+b'\r\n', wrapped_socket)

    pass_in_to_parse_ehlo(wrapped_socket)
    wrapped_socket.send(b"AUTH LOGIN\r\n")

    parsed_header = concatenate(look_for_newline(wrapped_socket))

    compare_equivalence_and_send(b""+parsed_header+b'\n', base64.encodebytes(b"Username:"), wrapped_socket,
                                 message_info['From'].encode())

    parsed_context = concatenate(look_for_newline(wrapped_socket))

    compare_equivalence_and_send(b""+parsed_context+b'\n', base64.encodebytes(b"Password:"), wrapped_socket, password.encode())

    verification = look_for_newline(wrapped_socket)
    parse_and_send(verification, b'2', b'3', b'5', b"MAIL FROM:"+b"<"+message_info['From'].encode()+b">\r\n", wrapped_socket)

    confirmation = look_for_newline(wrapped_socket)
    parse_and_send(confirmation, b'2', b'5', b'0', b"RCPT TO:"+b"<"+message_info['To'].encode()+b'>\r\n', wrapped_socket)

    data_confirm = look_for_newline(wrapped_socket)
    parse_and_send(data_confirm, b'2', b'5', b'0', b"DATA\r\n", wrapped_socket)

    look_for_newline(wrapped_socket)

    wrapped_socket.send(b"To: "+message_info['To'].encode()+b"\r\nFrom: "+message_info['From'].encode()+b"\r\nSubject: "+
                        message_info['Subject'].encode()+b'\r\n'+b"Date: "+message_info['Date'].encode()+b'\r\n\r\n'+message_text.encode()+b"\r\n"+
                        b"."+b"\r\n")

    final = look_for_newline(wrapped_socket)
    parse_and_send(final, b'2', b'5', b'0', b"QUIT\r\n", wrapped_socket)


def compare_equivalence_and_send(proposition1, proposition2, wrapped_socket, message):
    """
    :param proposition1:
    :param proposition2:
    :param wrapped_socket:
    :param message:
    :return:
    """
    if proposition1 == proposition2:
        wrapped_socket.send(base64.encodebytes(message)+b'\r\n')
    else:
        raise Exception("An error occurred verifying the username")


def concatenate(list):
    """
    :param list:
    :return:
    """
    list_as_string = b""
    for i in range(4, len(list) - 1):
        list_as_string = list_as_string + list[i]
    return list_as_string


def parse_and_send(line, code1, code2, code3, message, socket):
    """
    :param line:
    :param code1:
    :param code2:
    :param code3:
    :param message:
    :param socket:
    :return:
    """
    if line[0] == code1 and line[1] == code2 and line[2] == code3:
        socket.send(message)
    else:
        raise Exception("An error occurred")


def pass_in_to_parse_ehlo(socket):
    """
    :param socket:
    :return:
    """
    temporary_socket = []
    temporary_socket.append(b'1')
    temporary_socket.append(b'2')
    temporary_socket.append(b'3')
    temporary_socket.append(b'4')
    while temporary_socket[3].decode() != " ":
        temporary_socket = parse_extended_hello(socket)
    return temporary_socket


def look_for_newline(socket):
    """
    :param socket:
    :return:
    """
    text = b""
    first_line = []
    string = ""
    while text.decode() != "\r":
        text = socket.recv(1)
        string = string + text.decode()
        first_line.append(text)
    socket.recv(1)
    return first_line

def parse_extended_hello(socket):
        '''
        want to write loop that goes through looking for \r\n and then parses through them to find the dash.
        '''
        socket_data = look_for_newline(socket)
        while socket_data[3].decode() == "-":
            socket_data = look_for_newline(socket)
        return socket_data


# Utility functions


def get_formatted_date():
    """Get the current date and time, in a format suitable for an email date header.

    The constant TIMEZONE_NAME should be one of the standard pytz timezone names.

    tzlocal suggested by http://stackoverflow.com/a/3168394/1048186

    See RFC 5322 for details about what the timezone should be
    https://tools.ietf.org/html/rfc5322

    :return: Formatted current date/time value, as a string.
    """
    zone = tzlocal.get_localzone()
    print("zone =", zone)
    timestamp = datetime.datetime.now(zone)
    timestring = timestamp.strftime('%a, %d %b %Y %H:%M:%S %z')  # Sun, 06 Nov 1994 08:49:37 +0000
    return timestring


def print_all_timezones():
    """ Print all pytz timezone strings. """
    for tz in pytz.all_timezones:
        print(tz)


def get_mime_type(file_path):
    """Try to guess the MIME type of a file (resource), given its path (primarily its file extension)

    :param file_path: String containing path to (resource) file, such as './abc.jpg'
    :return: If successful in guessing the MIME type, a string representing the content
             type, such as 'image/jpeg'
             Otherwise, None
    :rtype: int or None
    """

    mime_type_and_encoding = mimetypes.guess_type(file_path)
    mime_type = mime_type_and_encoding[0]
    return mime_type


def get_file_size(file_path):
    """Try to get the size of a file (resource) in bytes, given its path

    :param file_path: String containing path to (resource) file, such as './abc.html'

    :return: If file_path designates a normal file, an integer value representing the the file size in bytes
             Otherwise (no such file, or path is not a file), None
    :rtype: int or None
    """

    # Initially, assume file does not exist
    file_size = None
    if os.path.isfile(file_path):
        file_size = os.stat(file_path).st_size
    return file_size


main()
