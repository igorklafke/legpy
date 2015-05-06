# -*- coding: cp860 -*-
from PyQt4.QtGui import *
import sys, getopt
import requests
import rarfile
import zipfile
import re
import os
import operator
from HTMLParser import HTMLParser
from easysettings import EasySettings

base_url = "http://legendas.tv"

settings = EasySettings("settings.conf")

def substitui_caracteres(texto):
    return re.sub('[^0-9a-zA-Z]+', '%20', texto).upper()

class LegPy():
    def login(self, usuario, senha):
        s = requests.Session()
        url = "%s/login" % base_url
        payload = {'data[User][username]':usuario, 'data[User][password]': senha, "data[lembrar]": "on"}
        r = s.post(url, payload)
        html = r.content

        if "<title>Login - Legendas TV</title>" in html:
            return 0
        else:
            return 1

    def inicia_busca(self, path):
        arquivos = os.listdir(path)

        for arq in arquivos:
            sub_path = '%s\%s' % (path, arq)
            if os.path.isdir(sub_path):
                sub_arquivos = os.listdir(sub_path)
                for sub_arq in sub_arquivos:
                    if not os.path.isdir('%s\%s' % (sub_path, sub_arq)):
                        self.busca_legenda(sub_path, sub_arq)
            else:
                self.busca_legenda(path, arq)

    def busca_legenda(self, path, nome):
        nome_up = nome.upper()
        if nome_up.endswith('.MKV') or nome_up.endswith('.MP4') or nome_up.endswith('.AVI'):
            nome_sem_ext = nome[:nome.rindex('.')]
            path_srt = '%s\%s.%s' % (path, nome_sem_ext, 'srt')
            if not os.path.exists(path_srt):
                print "buscando legenda para %s" % nome_sem_ext
                nome_pesquisa = substitui_caracteres(nome_sem_ext)

                url = "%s/legenda/busca/%s/1" % (base_url, nome_pesquisa)
                r = requests.get(url)

                html = r.text
                parser = self.PesquisaParser(path, nome_sem_ext)
                parser.feed(html)


    class PesquisaParser(HTMLParser):
        def __init__(self, path, nome_arquivo):
            HTMLParser.__init__(self)
            self.path_arquivos = path
            self.nome_arquivo = nome_arquivo
            self.termo_pesquisa = substitui_caracteres(nome_arquivo)

        def contem_todos_termos(self, texto):
            contem_termo = 1
            termos_array = self.termo_pesquisa.split('%20')
            tam = len(termos_array)
            i = 0
            #print texto
            while contem_termo and i < tam:
                contem_termo = termos_array[i] in texto.upper()
                termou = termos_array[i].upper()
                if not contem_termo and operator.eq(termou, 'BLURAY'):
                    contem_termo = 'BRRIP' in texto.upper()
                if operator.eq(termou, '720P'):
                	contem_termo = True
            	if operator.eq(termou, 'DIMENSION'):
            		contem_termo = True
            	if operator.eq(termou, 'PROPER'):
            		contem_termo = True
            	if operator.eq(termou, 'X264'):
            		contem_termo = True
            	if operator.eq(termou, 'YIFY'):
            		contem_termo = True
            	if operator.eq(termou, 'XVID'):
            		contem_termo = True
                i += 1
                #print termou
                #print contem_termo
            return contem_termo

        def nome_arquivo_igual(self, nome):
            nome = nome[:nome.rindex('.')]
            nome = substitui_caracteres(nome)
            igual = operator.eq(nome, self.termo_pesquisa)
            if not igual and 'BLURAY' in self.termo_pesquisa:
                igual = operator.eq(nome, self.termo_pesquisa.replace('BLURAY', 'BRRIP'))
            return igual

        def extrair(self, ziprar):
            extensao = 'srt'
            destino = '%s\%s.%s' % (self.path_arquivos, self.nome_arquivo, extensao)
            cont_srts = 0
            nome_srt = ''
            baixou = 0
            for f in ziprar.infolist():
            	fname = f.filename
            	if len(os.path.split(fname)) > 1:
            		fname = os.path.split(f.filename)[1]
                if self.nome_arquivo_igual(fname):
                    print "nome arquivo igual"
                    with open(destino, "wb") as out_srt:
                        out_srt.write(ziprar.read(f))
                        baixou = 1
                else:
                    if (fname.upper().endswith(extensao.upper())):
                        cont_srts += 1
                        nome_srt = f
            if not baixou and operator.eq(cont_srts, 1):
                with open(destino, "wb") as out_srt:
                    out_srt.write(ziprar.read(nome_srt))

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                link = attrs[0][1]
                if "/download/" in link:
                    if self.contem_todos_termos(link):
                        array_link = link.split('/')
                        id_arquivo = array_link[2]
                        link_download = '%s/downloadarquivo/%s' % (base_url, id_arquivo)
                        print "legenda encontrada"
                        print "baixando a partir de %s" % link_download

                        s = requests.Session()
                        settings = EasySettings("settings.conf")
                        
                        url = "%s/login" % base_url
                        payload = {'data[User][username]':settings.get("u"), 'data[User][password]': settings.get("p"), "data[lembrar]": "on"}
                        s.post(url, payload)

                        req = s.get(link_download)
                        rar_bytes = req.content
                        temp_rar = '%s\%s' % (self.path_arquivos, "temp.rar")
                        with open(temp_rar, "wb") as out_file:
                            out_file.write(rar_bytes)
                        
                        if zipfile.is_zipfile(temp_rar):
                            zf = zipfile.ZipFile(temp_rar)
                            self.extrair(zf)
                            zf.close()
                        else:
                            rf = rarfile.RarFile(temp_rar)
                            self.extrair(rf)
                        os.remove(temp_rar)

class SearchDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("Buscar Legendas")

        layout = QGridLayout()

        path_label = QLabel(u"Caminho v¡deos")
        self.path_edit = QLineEdit()

        button = QPushButton("Buscar")

        layout.addWidget(path_label, 0, 0)
        layout.addWidget(self.path_edit, 0, 1)
        layout.addWidget(button, 1, 1)

        path_salvo = settings.get("path")
        if path_salvo:
            self.path_edit.setText(path_salvo)

        self.setLayout(layout)

        button.clicked.connect(self.click_busca)

    def click_busca(self):
        path = self.path_edit.text()
        if path:
            settings.set("path", path)
            settings.save()
            lp.inicia_busca(path)
            self.close()

class LoginDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("Login Legendas.TV")
        layout = QGridLayout()
        usuario_label = QLabel(u"Usu rio")
        senha_label = QLabel("Senha")

        self.status_label = QLabel("")

        self.usuario_edit = QLineEdit()
        self.senha_edit = QLineEdit()
        self.senha_edit.setEchoMode(QLineEdit.Password)

        button = QPushButton("Login")

        layout.addWidget(usuario_label, 0, 0)
        layout.addWidget(self.usuario_edit, 0, 1)
        layout.addWidget(senha_label, 1, 0)
        layout.addWidget(self.senha_edit, 1, 1)

        layout.addWidget(self.status_label)

        layout.addWidget(button, 3, 1)
        
        self.setLayout(layout)

        button.clicked.connect(self.login)

    def login(self):
        usuario = "%s" % self.usuario_edit.text()
        senha = "%s" % self.senha_edit.text()
        if lp.login(usuario, senha):
            print "logou pelo form"
            settings.set("u", usuario)
            settings.set("p", senha)
            settings.save()
            self.close()
            searchDialog.show()
        else:
            print "erro no login pelo form"
            self.close()         
        

app = QApplication(sys.argv)

lp = LegPy()
searchDialog = SearchDialog()

usuario = settings.get("u")
senha = settings.get("p")
logou = 0

if usuario and senha:
    if lp.login(usuario, senha):
        logou = 1

if logou:
    searchDialog.show()
else:
    loginDialog = LoginDialog()
    loginDialog.show()

app.exec_()