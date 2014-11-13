# -*- coding: cp860 -*-
import sys, getopt
import requests
import rarfile
import zipfile
import re
import os
import operator
from HTMLParser import HTMLParser

base_url = "http://legendas.tv"

def substitui_caracteres(texto):
    return re.sub('[^0-9a-zA-Z]+', '%20', texto).upper()

class LegPy():
    def __init__(self, path):
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
            while contem_termo and i < tam:
                contem_termo = termos_array[i] in texto.upper()
                i += 1
            return contem_termo

        def nome_arquivo_igual(self, nome):
            nome = nome[:nome.rindex('.')]
            nome = substitui_caracteres(nome)
            return operator.eq(nome, self.termo_pesquisa)

        def extrair(self, ziprar):
            extensao = 'srt'
            destino = '%s\%s.%s' % (self.path_arquivos, self.nome_arquivo, extensao)
            cont_srts = 0
            nome_srt = ''
            baixou = 0
            for f in ziprar.infolist():
                if self.nome_arquivo_igual(f.filename):
                    with open(destino, "wb") as out_srt:
                        out_srt.write(ziprar.read(f))
                        baixou = 1
                else:
                    if (f.filename.upper().endswith(extensao.upper())):
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
                        req = requests.get(link_download)
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

args = sys.argv[1:]
if len(args) > 0:
    path_arquivos = args[0]
    if len(path_arquivos) > 0:
        LegPy(path_arquivos)
