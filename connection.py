# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from constants import *
from base64 import b64encode
from os import listdir
from os.path import isfile, join, getsize


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        self.s = socket            # Socket del cliente.
        self.d = './' + directory  # Directiorio actual.
        self.buffer = ''           # Cola de comandos. 
        self.active = True         # Nos dice si el cliente termino la conexión.
        self.data = ''             # Datos que se van a enviar al cliente.

    def send(self, message):
        # Envia el mensaje al cliente.
        # FALTA: Hacerlo bien.
        self.data = ''
        self.s.send(message.encode('ascii'))

    def _build_message(self, status):
        """
        Estos mensajes estan construidos por el codigo de respuesta,
        seguida de un espacio, seguido de un mensaje de error y
        datos del server si es que los hay.
        """
        message = '%s %s %s' % (status, error_messages[status], EOL)
        if len(self.data) != 0:
            message += str(self.data)
            message += EOL  # Completa el mensaje con un fin de línea.
        return message

    def get_file_listing(self):
        try:
            files = [f for f in listdir(self.d) if isfile(join(self.d, f))]
            self.data = EOL.join(files) + EOL
            return CODE_OK
        except Exception:
            return FILE_NOT_FOUND

    def get_slice(self, filename, offset, size):
        try:
            offset, size = int(offset), int(size)
        except ValueError:
            '''
            Levantar esta excepcion significa que llegaron argumentos
            invalidos y parser_command tiene que manejalo.
            '''
            raise

        path = join(self.d, filename)
        file = open(join(self.d, filename), 'rb')
        file.seek(offset)
        data = file.read(size)
        data = b64encode(data).decode('ascii')
        self.data = data
        return CODE_OK

    def get_metadata(self, filename):
        '''
        FALTA: Chequear que el filename sea valido, usando VALID_CHARS de los
        profes.

        Onda hacer una funcion que chequea eso y de paso que exista, de lo
        contrario tiramos un FILE_NOT_FOUND y nos evitamos un try feo.
        '''
        try:
            '''
            Obtenemos el tamaño del archivo en el directorio self.d y lo
            guardamos en self.data.
            '''
            size = getsize(join(self.d, filename))
            self.data = str(size)
            return CODE_OK
        except Exception:
            return FILE_NOT_FOUND

    def quit(self):
        self.active = False
        return CODE_OK

    def _normalize_command(self, command):
        '''
        Ejemplo:
        Llamar a self._normalize_command('get_metadata home.txt') produce una
        una tupla de la forma: ('get_metadata', ['home.txt'])

        Donde el primer elemento de la lista es el comando y el resto son
        los argumentos si es que los hay.
        '''
        try:
            command, args = command.split(' ', 1)
            return command, args.split(' ')
        except ValueError:
            return command, None

    def parser_command(self, command):
        '''
        Esta funcion llama al metodo correspondiente al comando solicitado.
        
        Ademas:
            1. Chequea que no haya un caracter \n fuera de un terminador de
               pedido.
            2. Normaliza el comando a una forma comoda para nosotros.
        '''
        if '\n' in command:
            return BAD_EOL
        else:
            # Normalizamos el comando.
            command, args = self._normalize_command(command)

        print("Request: " + command)

        try:
            if command in ['quit', 'get_file_listing'] and args:
                raise TypeError
            elif command == 'get_file_listing':
                return self.get_file_listing()
            elif command == 'get_metadata':
                return self.get_metadata(*args)
            elif command == 'get_slice':
                return self.get_slice(*args)
            elif command == 'quit':
                return self.quit()
            else:
                return INVALID_COMMAND
        except (TypeError, ValueError):
            return INVALID_ARGUMENTS

    def _read_buffer(self):
        while EOL not in self.buffer and self.active:
            data = self.s.recv(BUFSIZE).decode("ascii")
            self.buffer += data
            if len(data) == 0:
                self.active = False
        if EOL in self.buffer:
            response, self.buffer = self.buffer.split(EOL, 1)
            return response
        else:
            return ''

    def handle(self):
        # Atiende eventos de la conexión hasta que termina.
        while self.active:
            try:
                command = self._read_buffer()
                if len(command) != 0: 
                    status = self.parser_command(command)
                    print(status)
                    # Desconectamos si ocurrio un error fatal.
                    if fatal_status(status):
                        self.active = False
                    # Construimos un mensaje.
                    message = self._build_message(status)
                    # Enviamos el mensaje al cliente.
                    self.send(message)
            except:
                pass
