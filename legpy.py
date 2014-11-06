import sys, getopt
import requests
import rarfile
import re
import os
import operator
from HTMLParser import HTMLParser

base_url = "http://legendas.tv"


class LegPy():
    def __init__(self, path):
        arquivos = os.listdir(path)

        for arq in arquivos:
            arq = arq.upper()
            if arq.endswith('.MKV') or arq.endswith('.MP4') or arq.endswith('.AVI'):
                nome_sem_ext = arq[:arq.rindex('.')]
                nome_pesquisa = re.sub('[^0-9a-zA-Z]+', '%20', nome_sem_ext).upper()
                url = "%s/legenda/busca/%s/1" % (base_url, nome_pesquisa)
                r = requests.get(url)
                html = r.text
                parser = self.PesquisaParser(path, nome_pesquisa)
                parser.feed(html)

    class PesquisaParser(HTMLParser):
        def __init__(self, path, termo):
            HTMLParser.__init__(self)
            self.path_arquivos = path
            self.termo_pesquisa = termo

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
            nome = re.sub('[^0-9a-zA-Z]+', '%20', nome).upper()
            return operator.eq(nome, self.termo_pesquisa)

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                link = attrs[0][1]
                if "/download/" in link:
                    if self.contem_todos_termos(link):
                        array_link = link.split('/')
                        id_arquivo = array_link[2]
                        link_download = '%s/downloadarquivo/%s' % (base_url, id_arquivo)
                        print link
                        print link_download
                        req = requests.get(link_download)
                        rar_bytes = req.content
                        with open("temp.rar", "wb") as out_file:
                            out_file.write(rar_bytes)
                        rf = rarfile.RarFile('temp.rar')
                        for f in rf.infolist():
                            if self.nome_arquivo_igual(f.filename):
                                print(f.filename)
                                destino = "%s\%s" % (self.path_arquivos, f.filename)
                                with open(destino, "wb") as out_srt:
                                    out_srt.write(rf.read(f))
                        os.remove("temp.rar")

args = sys.argv[1:]
if len(args) > 0:
    path_arquivos = args[0]
    if len(path_arquivos) > 0:
        LegPy(path_arquivos)