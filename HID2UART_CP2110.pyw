﻿# coding:utf-8
#/usr/bin/python

import sys
import queue

from PyQt5 import QtCore

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QLabel, QComboBox, QTextBrowser, QScrollBar, QHBoxLayout, QVBoxLayout, QAction, QMessageBox
from PyQt5.QtGui import QFont

import pywinusb.hid as hid

class Thread(QtCore.QThread):
    msg_ready = QtCore.pyqtSignal(list)

    def __init__(self, func):
        super(QtCore.QThread, self).__init__()
        self.func = func

    def run(self):
        while True:
            msg = []
            items = self.func()
            
            if items:
                for i in items:
                    msg.append(i)

                self.msg_ready.emit(msg)

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.current_device = 0     # 当前设备编号
        self.previous_device = 0    # 之前设备编号

        self.hid_device = None      # 设备
        
        self.queue = queue.Queue()  # 创建队列
        
        self.device_label = QLabel("Device List:")
        self.device_combobox = QComboBox()
        self.device_scan()

        self.baudrate_label = QLabel("Baudrate:")
        self.baudrate_combobox = QComboBox()
        self.baudrate_combobox.addItem("9600")
        self.baudrate_combobox.addItem("38400")
        self.baudrate_combobox.addItem("115200")
        self.baudrate_combobox.currentIndexChanged.connect(self.baudrate_change)

        self.open_pushbutton = QPushButton("Open")
        # self.open_pushbutton.setToolTip('Open/Close the CP2110')
        self.open_pushbutton.clicked.connect(self.device_openclose)
        
        self.clear_pushbutton = QPushButton("Clear")
        self.clear_pushbutton.clicked.connect(self.rx_textbrowser_clear)

        layout_list = QHBoxLayout()

        layout_list.addWidget(self.device_label)
        layout_list.addWidget(self.device_combobox)
        layout_list.addWidget(self.baudrate_label)
        layout_list.addWidget(self.baudrate_combobox)
        layout_list.addWidget(self.open_pushbutton)
        layout_list.addWidget(self.clear_pushbutton)

        layout_list.addStretch()
        
        self.rx_textbrowser = QTextBrowser()
        self.rx_textbrowser.setFont(QFont("Consolas", 10))
        # self.rx_textbrowser.setFont(QFont("Courier New", 10))

        self.bar = QScrollBar()
        self.bar = self.rx_textbrowser.verticalScrollBar()
        self.bar.setValue(self.bar.maximum());

        self.status_label = QLabel("Status:")
        
        layout = QVBoxLayout()

        layout.addLayout(layout_list)
        layout.addWidget(self.rx_textbrowser)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        self.thread = Thread(self.queue_monitor)
        self.thread.msg_ready.connect(self.rx_textbrowser_update)
        self.thread.start()

    def queue_monitor(self):
        if self.queue.qsize():
            try:
                msgs = self.queue.get()
                return msgs

            except queue.Empty:
                pass

    string = ""
    def rx_textbrowser_update(self, item):
        if (item[0] == 1):
            if (item[1] == 10):
                self.rx_textbrowser.append(self.string)
                self.bar.setValue(self.bar.maximum())
                self.string = ""
            elif (item[1] != 13):    
                self.string = self.string + chr(item[1])
        
    def report_recv_handler(self, data):
        self.queue.put(data)
        
    def rx_textbrowser_clear(self):
        self.rx_textbrowser.clear()
        
    def baudrate_change(self):
        if self.device_combobox.count() == 0:
            self.status_label.setText("Status: " + "no CP2110 device detected!")
            return

        if (self.hid_device.is_opened()):
            self.uart_config(self.baudrate_combobox.currentIndex())

    def device_change(self):
        print("device_change")

        if self.device_combobox.count() == 0:
            self.status_label.setText("Status: " + "no CP2110 device detected!")
            return

        self.current_device = self.device_combobox.currentIndex() #获取当前设备索引号
        
        if self.previous_device != self.current_device:
            self.open_pushbutton.setText("Open")
            self.status_label.setText("Status: ")
        else: 
            if self.hid_device.is_opened():
                self.open_pushbutton.setText("Close")
            else:
                self.open_pushbutton.setText("Open")

    def uart_onoff(self, onoff):
        buff    = [0x00] * 64
        buff[0] = 0x41 # Report ID = 0x41 Get/Set UART Enable

        if (onoff == 1):
            buff[1] = 0x1  # UART enable
        else:
            buff[1] = 0x0  # UART disable

        self.hid_device.send_feature_report(buff)

    def uart_config(self, baudrate_idx):
        buff    = [0x00] * 64
        buff[0] = 0x50 # Report ID = 0x41 Get/Set UART Enable

        if baudrate_idx == 0:   #9600
            buff[1] = 0x0
            buff[2] = 0x0
            buff[3] = 0x25
            buff[4] = 0x80
        elif baudrate_idx == 1: #38400    
            buff[1] = 0x0
            buff[2] = 0x0
            buff[3] = 0x96
            buff[4] = 0x00
        elif baudrate_idx == 2: #115200    
            buff[1] = 0x0
            buff[2] = 0x01
            buff[3] = 0xC2
            buff[4] = 0x00
        else:                   #9600
            buff[1] = 0x0
            buff[2] = 0x0
            buff[3] = 0x25
            buff[4] = 0x80                

        buff[5] = 0x0
        buff[6] = 0x0
        buff[7] = 0x3
        buff[8] = 0x0

        self.hid_device.send_feature_report(buff)

    def device_scan(self):
        self.device_combobox.__init__()

        self.all_devices = hid.HidDeviceFilter(vendor_id=0x10C4, product_id=0xEA80).get_devices()

        for i in self.all_devices:
            id_information = "vId= 0x{0:04X}, pId= 0x{1:04X}, ppId= 0x{2:04X}".format(i.vendor_id, i.product_id, i.parent_instance_id)
            self.device_combobox.addItem(id_information)

        if self.all_devices:
            self.hid_device = self.all_devices[self.current_device]

        self.device_combobox.currentIndexChanged.connect(self.device_change)

    def device_openclose(self):
        if self.device_combobox.count() == 0:
            self.status_label.setText("Status: " + "no CP2110 device detected!")
            return

        # 与之前选择的设备相同 
        if self.previous_device == self.current_device:
            if self.hid_device.is_opened():
                self.hid_device.close()
                self.open_pushbutton.setText("Open")
                print(self.hid_device, "Closed")
                self.status_label.setText("Status: ")
            else:
                self.hid_device.open()
                self.hid_device.set_raw_data_handler(self.report_recv_handler)
                self.reports = self.hid_device.find_output_reports()
                self.feature_report = self.hid_device.find_feature_reports()
                # in_reports   = self.hid_device.find_input_reports()

                self.uart_onoff(1)
                self.uart_config(self.baudrate_combobox.currentIndex())

                # for i in self.feature_report:
                #     print(i.get(False))
                
                self.status_label.setText("Status: " + self.hid_device.product_name + " " + self.hid_device.vendor_name + " " + self.hid_device.serial_number)
                print(self.hid_device, "opend")
                
                self.open_pushbutton.setText("Close")
        else:
            self.hid_device.close()
            print(self.hid_device, "Closed")

            self.hid_device = self.all_devices[self.current_device]
            self.previous_device = self.current_device
            self.hid_device.open()
            print(self.hid_device, "Opened")
            self.hid_device.set_raw_data_handler(self.report_recv_handler)
            self.reports = self.hid_device.find_output_reports()
            self.feature_report = self.hid_device.find_feature_reports()

            # in_reports   = self.hid_device.find_input_reports()
            
            self.uart_onoff(1)
            self.uart_config(self.baudrate_combobox.currentIndex())

            # for i in self.feature_report:
            #     print(i)
            #     print(i.get(False))

            self.status_label.setText("Status: " + self.hid_device.product_name + " " + self.hid_device.vendor_name + " " + self.hid_device.serial_number)

            self.open_pushbutton.setText("Close")

class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.title = 'CP2110 HID USB-to-UART'
        
        self.left   = 400
        self.top    = 300
        self.width  = 800
        self.height = 600
        
        self.initUI()
 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        mainMenu = self.menuBar() 

        fileMenu   = mainMenu.addMenu('File')
        helpMenu   = mainMenu.addMenu('Help')

        scanButton = QAction('Scan', self)
        scanButton.setShortcut('Ctrl+S')
        scanButton.setStatusTip('Scan devices')
        scanButton.triggered.connect(self.scan)
        fileMenu.addAction(scanButton)

        exitButton = QAction('Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        aboutButton = QAction('About', self)
        aboutButton.setShortcut('Ctrl+A')
        aboutButton.setStatusTip('About application')
        aboutButton.triggered.connect(self.about)
        helpMenu.addAction(aboutButton)

        self.widget = MainWidget()
        self.setCentralWidget(self.widget)

        # self.statusBar().showMessage('Message in statusbar.')
        self.show()

    def about(self):
        QMessageBox.question(self, 'About', "CP2110 USB-to-UART\r\nVersion: 1.0\r\nAuthor: lgnq", QMessageBox.Ok, QMessageBox.Ok)

    def scan(self):
        self.widget.device_scan()    

if __name__ == '__main__':
    app = QApplication(sys.argv)

    ex = App()
    
    sys.exit(app.exec_())
    