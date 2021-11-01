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

__author__ = "Federico Turco"
__copyright__ = "Copyright 2021, Federico Turco"

#__credits__ = [""]
__license__ = "MIT"
__version__ = "0.1 beta"
__maintainer__ = "Federico Turco"
#__email__ = ""
__status__ = "Development"

import json
import logging
import traceback
import socket
import crccheck
import serial
from utility import *

config = json.loads(open("config.json", "r").read())
crc16_ModBus = crccheck.crc.Crc16Modbus()

# Configuro il logging
logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(message)s', level=applyVerbose(config["verbose"]))

logging.info("--------------------------------")
logging.info("  Gateway ModBus TCP <-> RTU")
logging.info("")
logging.info("  Version: " + __version__)
logging.info("  Author: " + __author__)
logging.info("--------------------------------")
logging.info("")

# ---------------------------------------
# ------ Apro la socket in ascolto ------
# ---------------------------------------
logging.info("Starting server on " + config["tcp"]["address"] + ":" + str(config["tcp"]["port"]))

s = socket.socket()
s.bind((config["tcp"]["address"], config["tcp"]["port"]))
s.listen(5)
s.settimeout(1)

# ---------------------------------------
# ------ Apro la porta seriale ----------
# ---------------------------------------

# Prendo il terzo carattere per gli stop bits
stopBits = int(config["serial"]["configuration"][2:3])

# Se len > 1 sono nel caso 1.5
if(len(config["serial"]["configuration"][2:]) > 1):
    stopBits = 1.5

ser = serial.Serial(
    port=config["serial"]["port"],
    baudrate=config["serial"]["baud"],
    parity=config["serial"]["configuration"][1],
    stopbits=stopBits,
    bytesize=int(config["serial"]["configuration"][0])
    )

ser.timeout = float(config["serial"]["timeout"]) / 1000

lastConfigSerial = 255    # Slave ID 255 considero standard   

logging.debug("Configuro seriale standard")
printSerialConfig(ser)


while True:

    try:
        client_sock, address = s.accept()  # Rimane in attesa max 30 sec poi passa avanti
        logging.info('Accepted connection from %s:%s' % (address[0], address[1]))

        try:
            buffer = client_sock.recv(1024)

            #logging.debug("Buffer rx TCP:")
            #logging.debug(list(buffer))
            logging.debug("<- Rx TCP: " + formatList(buffer))

            # Controllo protocol identifier che sia 00 00
            if(buffer[2] != 0 or buffer[3] != 0):
                logging.error("Protocol identifier non valido [" + formatList(buffer[2:4])[:-1] + "], per ModBus TCP deve essere 0")
                raise Exception

            messageLen = int(buffer[4] << 8) + int(buffer[5])
            slaveId = buffer[6]

            # debug
            #logging.debug("Len tx 485: " + str(messageLen)) 

            responseLen = 0

            # FC01, FC02
            if(buffer[7] == 0x01 or buffer[7] == 0x02):
                responseLen = int(((int(buffer[10]) << 8) + int(buffer[11])) / 8) + int(((int(buffer[10]) << 8) + int(buffer[11])) % 8 != 0) + 5 # 1 slave id, 1 FC, 1 len, 2 byte CRC

            # FC03, FC04
            elif(buffer[7] == 0x03 or buffer[7] == 0x04):
                responseLen = (((int(buffer[10]) << 8) + int(buffer[11])) * 2) + 5 # 1 slave id, 1 FC, 1 len, 2 byte CRC
            
            # FC05, FC06 
            elif(buffer[7] == 0x05 or buffer[7] == 0x06):
                responseLen = 8     # Risposta a lunghezza fissa di 8 bytes

            # FC15, FC16
            elif(buffer[7] == 0x0F or buffer[7] == 0x10):
                responseLen = 8     # Risposta a lunghezza fissa di 8 bytes

            # FC08
            elif(buffer[7] == 0x08):
                responseLen = 6     # Risposta a lunghezza fissa di 6 bytes

            # Function code not found
            else:
                logging.error("Function code non valido: " + formatList(buffer[7:8]))
                raise Exception

            # debug
            #logging.debug("Len rx 485: " + str(responseLen)) 

            toSend485 = []

            # Il pacchetto da inviare su 485 lo costruisco spazzolando il buffer dal byte 6
            for i in range(0, messageLen):
                toSend485.append(buffer[i + 6])

            # Aggiungo il CRC ModBus
            crc = crc16_ModBus.calc(toSend485)

            toSend485.append(0xFF & crc)
            toSend485.append(0xFF & (crc >> 8))

            #logging.debug("Buffer tx 485")
            #logging.debug(toSend485)
            logging.debug("-> Tx 485: " + formatList(toSend485))

            # ID da gestire in modo personalizzato
            if("slaves" in config["serial"]):

                # Cerco eventuale configurazione specifica
                if(str(slaveId) in config["serial"]["slaves"]):
                    if(config["serial"]["slaves"][str(slaveId)]["enable"]):
                        if(lastConfigSerial != slaveId):

                            # Salvo l'ID della configurazione specifica
                            lastConfigSerial = slaveId
                            
                            # Prendo il terzo carattere per gli stop bits
                            stopBits = int(config["serial"]["slaves"][str(slaveId)]["configuration"][2:3])

                            # Se len > 1 sono nel caso 1.5
                            if(len(config["serial"]["slaves"][str(slaveId)]["configuration"][2:]) > 1):
                                stopBits = 1.5

                            ser.close()

                            logging.debug("Configuro seriale specifica per slave ID: " + str(slaveId))
                            
                            ser = serial.Serial(
                                port=config["serial"]["slaves"][str(slaveId)]["port"],
                                baudrate=config["serial"]["slaves"][str(slaveId)]["baud"],
                                parity=config["serial"]["slaves"][str(slaveId)]["configuration"][1],        # string
                                stopbits=stopBits,                                                          # int or float
                                bytesize=int(config["serial"]["slaves"][str(slaveId)]["configuration"][0])
                            )

                            printSerialConfig(ser)

                            ser.timeout = float(config["serial"]["slaves"][str(slaveId)]["timeout"]) / 1000
                        
                        else:
                            logging.debug("Configurazione seriale ok per slave ID: " + str(slaveId) + ", non devo riconfigurarla")

                    else:
                        # ID ModBus corrente non abilitato
                        logging.error("Slave ID: " + str(slaveId) + " non abilitato nel file config.json")
                        client_sock.close()
                        raise Exception

                # Ripristino eventuale configurazione standard
                else:

                    # Se la seriale non era gia' aperta con una configurazione standard la riconfiguro
                    if(lastConfigSerial != 255):
                        # Prendo il terzo carattere per gli stop bits
                        stopBits = int(config["serial"]["configuration"][2:3])

                        # Se len > 1 sono nel caso 1.5
                        if(len(config["serial"]["configuration"][2:]) > 1):
                            stopBits = 1.5

                        lastConfigSerial = 255
                        ser.close()

                        logging.debug("Riconfiguro la seriale standard")

                        # Riconfiguro la seriale alla configurazione
                        ser = serial.Serial(
                            port=config["serial"]["port"],
                            baudrate=config["serial"]["baud"],
                            parity=config["serial"]["configuration"][1],        # string
                            stopbits=stopBits,                                                          # int or float
                            bytesize=int(config["serial"]["configuration"][0])
                        )

                        ser.timeout = float(config["serial"]["timeout"]) / 1000
                        
                        printSerialConfig(ser)

            #ser.open() # Gia' aperta dal blocco precedente se contiene il parametro port
            ser.write(toSend485)
            
            received485 = ser.read(responseLen)

            logging.debug("<- Rx 485: " + formatList(received485))
            
            # Controllo timeout lettura
            if(len(received485) == 0):
                logging.error("Timeout risposta 485")
                raise Exception

            # Controllo il CRC del pacchetto ricevuto
            if(not checkCrcModBus(received485)):
                # Il log e' gia' inserito nella funzione checkCrcModBus()
                raise Exception

            # Controllo la lunghezza del pacchetto ricevuto
            elif(len(received485) < responseLen):
                logging.error("Lunghezza pacchetto ricevuto insufficiente")
                raise Exception

            #logging.debug("Buffer rx 485:")
            #logging.debug(list(received485))

            response = []
            response.append(buffer[0])  #   0001: Transaction Identifier
            response.append(buffer[1])  #   0001: Transaction Identifier
            response.append(buffer[2])  #   0000: Protocol Identifier
            response.append(buffer[3])  #   0000: Protocol Identifier
            response.append(0xFF & (((responseLen) - 2)  >> 8)) #   0000: Bytes to follow
            response.append(0xFF & ((responseLen) - 2))         #   0010: Bytes to follow

            for i in range(0, (responseLen) - 2):
                response.append(received485[i])

            #logging.debug("Buffer tx TCP:")
            #logging.debug(response)
            logging.debug("-> Tx TCP: " + formatList(response))

            client_sock.send(bytes(response))
            client_sock.close()
                

        except Exception as err:
            try:
                client_sock.close()
            except:
                pass

            #logging.error(str(err))
            #logging.error(str(traceback.format_exc()))

    except Exception as err:
        pass
        #logging.error(str(err))
        #logging.error(str(traceback.format_exc()))
