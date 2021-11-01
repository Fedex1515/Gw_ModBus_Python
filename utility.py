#!/usr/bin/env python

# Copyright (c) 2021 Federico Turco

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

#__author__ = "Federico Turco"
#__copyright__ = "Copyright 2021, Federico Turco"

#__credits__ = [""]
#__license__ = "MIT"
#__version__ = ""
#__maintainer__ = "Federico Turco"
#__email__ = ""
#__status__ = "Development"

import logging
import crccheck

crc16_ModBus = crccheck.crc.Crc16Modbus()

def printSerialConfig(ser):
    """
    Stampa la configurazione della seriale passata come parametro
    """
    logging.debug(" -> port: " + ser.port)
    logging.debug(" -> baudrate: " + str(ser.baudrate))
    logging.debug(" -> parity: " + ser.parity)
    logging.debug(" -> stopbits: " + str(ser.stopbits))
    logging.debug(" -> byteseize: " + str(ser.bytesize))
    logging.debug(" -> timeout: " + str(ser.timeout))

def checkCrcModBus(buffer):
    """
    Controlla il crc della list passata come parametro
    """

    # Se il buffer e' u bytearray lo converto in list
    if(type(buffer) != list):
        buffer = list(buffer)

    toCalc = []

    for i in range(0, len(buffer) - 2):
        toCalc.append(buffer[i])

    crc = crc16_ModBus.calc(toCalc)

    crc_HB = (0xFF & (crc >> 8))
    crc_LB = (0xFF & crc)

    if(crc_LB == buffer[-2] and crc_HB == buffer[-1]):
        return True
    
    else:
        logging.error("Errore pacchetto crc, ricevuto: [" + hex(crc_LB) + ", " + hex(crc_HB) + "] calcolato: [" + hex(buffer[-2]) + ", " + hex(buffer[-1]) + "]")
        return False

def applyVerbose(level):
    """
    Applica la verbosita' passata come parametro
    - "CRITICAL"    -> 50
    - "ERROR"       -> 40
    - "WARNING"     -> 30
    - "INFO"        -> 20
    - "DEBUG"       -> 10
    - "NOTSET"      -> 0
    """
    
    if(level.upper() == "CRITICAL"):
        return logging.CRITICAL
    
    if(level.upper() == "ERROR"):
        return logging.ERROR
    
    if(level.upper() == "WARNING"):
        return logging.WARNING
    
    if(level.upper() == "INFO"):
        return logging.INFO
    
    if(level.upper() == "DEBUG"):
        return logging.DEBUG

    return False

def formatList(buffer):
    """
    Formatta i byte di un pacchetto in stringa di hex
    """
    output = ""

    for x in list(buffer):
        output += hex(x).split('x')[1].upper().zfill(2)
        output += " "
    
    return output