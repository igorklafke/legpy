# -*- coding: cp860 -*-
import sys, getopt
import requests
import rarfile
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
            nome = arq.upper()
            buscar = 0
            if os.path.isdir(nome):
                buscar = 1
                nome_sem_ext = arq
            else:
                if nome.endswith('.MKV') or nome.endswith('.MP4') or nome.endswith('.AVI'):
                    nome_sem_ext = arq[:arq.rindex('.')]
                    path_srt = '%s\%s.%s' % (path, nome_sem_ext, 'srt')
                    buscar = not os.path.exists(path_srt)
            if buscar:
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
                        rf = rarfile.RarFile(temp_rar)
                        for f in rf.infolist():
                            if self.nome_arquivo_igual(f.filename):
                                #fname = f.filename
                                fname = self.nome_arquivo
                                extensao = 'srt'
                                #fname = self.termo_pesquisa
                                destino = '%s\%s.%s' % (self.path_arquivos, fname, extensao)
                                with open(destino, "wb") as out_srt:
                                    out_srt.write(rf.read(f))
                        os.remove(temp_rar)

args = sys.argv[1:]
if len(args) > 0:
    path_arquivos = args[0]
    if len(path_arquivos) > 0:
        LegPy(path_arquivos)
