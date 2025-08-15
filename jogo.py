import pygame
import sys
import socket
import json
import ipaddress
import threading
import time
# --- Inicialização Pygame ---
try:
    pygame.init()
    pygame.font.init()
except Exception as e:
    print(f"Erro ao inicializar Pygame: {e}")
    sys.exit()

# --- PALETA DE CORES ---
FUNDO_ESCURO = (28, 28, 28)
CINZA_FUNDO = (40, 40, 40)
BRANCO_CLARO = (240, 240, 240)
COR_X = (255, 90, 90)  # Vermelho
COR_O = (60, 140, 255) # Azul
VERDE_DESTAQUE = (80, 255, 80)
VERMELHO_DESTAQUE = (255, 80, 80)

# --- Configurações da Tela ---
LARGURA, ALTURA = 600, 700
TAM_CELULA = 200
TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Jogo da Velha em Rede")

# --- Fontes ---
FONTE_TITULO = pygame.font.SysFont('Arial', 40, bold=True)
FONTE_PADRAO = pygame.font.SysFont('Arial', 32)
FONTE_MENOR = pygame.font.SysFont('Arial', 24)
FONTE_JOGADOR_GRANDE = pygame.font.SysFont('Arial', 150, bold=True)

CLOCK = pygame.time.Clock()

# --- Variáveis ---
estado_jogo = {'tabuleiro': None, 'vencedor': None, 'empate': False, 'turno': 'X', 'mensagens': []}
sock_comunicacao = None
oponente_addr = None
rodando_jogo = False
conectado = False
thread_rede = None

# Lock para evitar race conditions em variáveis compartilhadas
lock_rede = threading.Lock()

# --- Funções de Desenho da Interface ---
def desenhar_gradiente(surface, cor_inicio, cor_fim):
    """Desenha um gradiente vertical no fundo."""
    for y in range(ALTURA):
        r = cor_inicio[0] + (cor_fim[0] - cor_inicio[0]) * y / ALTURA
        g = cor_inicio[1] + (cor_fim[1] - cor_inicio[1]) * y / ALTURA
        b = cor_inicio[2] + (cor_fim[2] - cor_inicio[2]) * y / ALTURA
        pygame.draw.line(surface, (r, g, b), (0, y), (LARGURA, y))

def desenhar_texto_centralizado(surface, texto, fonte, cor, y):
    """Desenha um texto centralizado na tela."""
    texto_render = fonte.render(texto, True, cor)
    ret = texto_render.get_rect(center=(LARGURA // 2, y))
    surface.blit(texto_render, ret)

def desenhar_botao(x, y, largura, altura, cor, texto, fonte, texto_cor):
    """Desenha um botão retangular com bordas arredondadas."""
    ret = pygame.Rect(x, y, largura, altura)
    pygame.draw.rect(TELA, cor, ret, border_radius=20)
    txt_render = fonte.render(texto, True, texto_cor)
    TELA.blit(txt_render, txt_render.get_rect(center=ret.center))
    return ret

def desenhar_caixa_texto(x, y, largura, altura, texto, ativo, cor_borda):
    """Desenha uma caixa de texto com bordas arredondadas."""
    ret = pygame.Rect(x, y, largura, altura)
    pygame.draw.rect(TELA, BRANCO_CLARO, ret, border_radius=10)
    pygame.draw.rect(TELA, cor_borda, ret, 3, border_radius=10)
    txt_render = FONTE_PADRAO.render(texto, True, FUNDO_ESCURO)
    TELA.blit(txt_render, (ret.x + 10, ret.y + 10))
    return ret

def desenhar_tabuleiro(surface, tabuleiro):
    """Desenha o tabuleiro do jogo na tela."""
    if not tabuleiro:
        return
    pygame.draw.rect(surface, CINZA_FUNDO, (0, 0, LARGURA, LARGURA))
    for i in range(3):
        for j in range(3):
            x = j * TAM_CELULA
            y = i * TAM_CELULA
            rect = pygame.Rect(x, y, TAM_CELULA, TAM_CELULA)
            pygame.draw.rect(surface, FUNDO_ESCURO, rect, 3)
            if tabuleiro[i][j] != ' ':
                simbolo = tabuleiro[i][j]
                if simbolo == 'X':
                    cor_simbolo = COR_X
                elif simbolo == 'O':
                    cor_simbolo = COR_O
                else:
                    cor_simbolo = FUNDO_ESCURO 

                texto = FONTE_JOGADOR_GRANDE.render(simbolo, True, cor_simbolo)
                texto_rect = texto.get_rect(center=rect.center)
                surface.blit(texto, texto_rect)

# --- Funções da Lógica do Jogo da Velha (sem mudanças) ---
def criar_tabuleiro():
    """Cria um tabuleiro 3x3 vazio."""
    return [[' ' for _ in range(3)] for _ in range(3)]

def fazer_jogada(tabuleiro, linha, coluna, jogador):
    """Realiza uma jogada se for válida."""
    if 0 <= linha < 3 and 0 <= coluna < 3 and tabuleiro[linha][coluna] == ' ':
        tabuleiro[linha][coluna] = jogador
        return True
    return False

def verificar_vencedor(tabuleiro):
    """Verifica se há um vencedor e retorna o símbolo ('X' ou 'O')."""
    if not tabuleiro: return None
    for i in range(3):
        if tabuleiro[i][0] == tabuleiro[i][1] == tabuleiro[i][2] != ' ':
            return tabuleiro[i][0]
        if tabuleiro[0][i] == tabuleiro[1][i] == tabuleiro[2][i] != ' ':
            return tabuleiro[0][i]
    if tabuleiro[0][0] == tabuleiro[1][1] == tabuleiro[2][2] != ' ':
        return tabuleiro[0][0]
    if tabuleiro[0][2] == tabuleiro[1][1] == tabuleiro[2][0] != ' ':
        return tabuleiro[0][2]
    return None

def verificar_empate(tabuleiro):
    """Verifica se o jogo terminou em empate."""
    if not tabuleiro: return False
    for linha in tabuleiro:
        if ' ' in linha:
            return False
    return verificar_vencedor(tabuleiro) is None

# --- Funções da Lógica de Rede CORRIGIDAS ---
def get_ip_family(host):
"""Determina a família do endereço IP (IPv4 ou IPv6) e retorna a string."""
    try:
        ip = ipaddress.ip_address(host)
        return 'IPv4' if isinstance(ip, ipaddress.IPv4Address) else 'IPv6'
    except ValueError:
        return 'Inválido'

def criar_socket_comunicacao(protocolo, host, porta):
    """Cria e configura um socket para comunicação, tratando corretamente o IPv6."""
    try:
        addr_info = socket.getaddrinfo(host, porta, socket.AF_UNSPEC,
                                       socket.SOCK_STREAM if protocolo == 'tcp' else socket.SOCK_DGRAM)
        
        af, socktype, proto, canonname, sa = addr_info[0]

        sock = socket.socket(af, socktype, proto)
        
        return sock, sa
    
    except socket.gaierror as e:
        estado_jogo['mensagens'].append(f"Erro de endereço: {e}")
        return None, None
    except Exception as e:
        estado_jogo['mensagens'].append(f"Erro ao criar o socket: {e}")
        return None, None

def enviar_dados(sock, dados, protocolo, oponente_addr=None):
    """Serializa e envia os dados."""
    payload = json.dumps(dados).encode('utf-8')
    try:
        if protocolo == 'tcp':
            sock.sendall(payload)
        else:
            if oponente_addr:
                sock.sendto(payload, oponente_addr)
        return True
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        print(f"Erro de envio: {e}")
        return False
    except Exception as e:
        print(f"Erro ao enviar dados: {e}")
        return False

def receber_dados(sock, protocolo, buffer_size=4096):
    """Recebe e desserializa os dados."""
    try:
        if protocolo == 'tcp':
            sock.settimeout(0.1)
            payload = sock.recv(buffer_size)
            if not payload:
                return None, None
            return json.loads(payload.decode('utf-8')), None
        else:
            sock.settimeout(0.1)
            payload, addr = sock.recvfrom(buffer_size)
            if not payload:
                return None, None
            return json.loads(payload.decode('utf-8')), addr
    except socket.timeout:
        return None, None
    except (ConnectionResetError, ConnectionAbortedError) as e:
        print(f"Conexão perdida: {e}")
        return {'status': 'desconexao'}, None
    except Exception as e:
        print(f"Erro ao receber dados: {e}")
        return None, None

def thread_servidor_tcp(sock, addr):
    global sock_comunicacao, oponente_addr, rodando_jogo, estado_jogo, conectado
    
    with lock_rede:
        estado_jogo['mensagens'].append("Aguardando oponente...")
    
    try:
        sock.bind(addr)
        sock.listen(1)
        
        sock.settimeout(1.0)
        while rodando_jogo and not conectado:
            try:
                conn, addr = sock.accept()
                with lock_rede:
                    sock_comunicacao = conn
                    oponente_addr = addr
                    estado_jogo['mensagens'] = ["Oponente conectado!"]
                    conectado = True
                sock_comunicacao.settimeout(0.1)
            except socket.timeout:
                continue
    except Exception as e:
        with lock_rede:
            estado_jogo['mensagens'].append(f"Erro no servidor TCP: {e}")
            rodando_jogo = False
        return

    while rodando_jogo:
        dados, _ = receber_dados(sock_comunicacao, 'tcp')
        if dados:
            if dados.get('status') == 'desconexao':
                with lock_rede:
                    estado_jogo['mensagens'].append("Conexão perdida com o oponente.")
                    rodando_jogo = False
            else:
                with lock_rede:
                    estado_jogo['tabuleiro'] = dados.get('tabuleiro', estado_jogo['tabuleiro'])
                    estado_jogo['turno'] = 'X' if estado_jogo['turno'] == 'O' else 'O'
        time.sleep(0.01)
    
    if sock_comunicacao:
        sock_comunicacao.close()
    if sock:
        sock.close()

def thread_cliente_tcp(sock, addr):
    global sock_comunicacao, oponente_addr, rodando_jogo, estado_jogo, conectado
    
    host_display = addr[0]
    with lock_rede:
        estado_jogo['mensagens'].append(f"Conectando a {host_display}:{addr[1]}...")
    
    try:
        sock.connect(addr)
        with lock_rede:
            sock_comunicacao = sock
            oponente_addr = addr
            estado_jogo['mensagens'] = ["Conectado ao servidor!"]
            conectado = True
        sock_comunicacao.settimeout(0.1)
    except ConnectionRefusedError:
        with lock_rede:
            estado_jogo['mensagens'].append("Conexão recusada pelo servidor.")
            rodando_jogo = False
        return
    except Exception as e:
        with lock_rede:
            estado_jogo['mensagens'].append(f"Erro ao conectar: {e}")
            rodando_jogo = False
        return

    while rodando_jogo:
        dados, _ = receber_dados(sock_comunicacao, 'tcp')
        if dados:
if dados.get('status') == 'desconexao':
                with lock_rede:
                    estado_jogo['mensagens'].append("Conexão perdida com o oponente.")
                    rodando_jogo = False
            else:
                with lock_rede:
                    estado_jogo['tabuleiro'] = dados.get('tabuleiro', estado_jogo['tabuleiro'])
                    estado_jogo['turno'] = 'X' if estado_jogo['turno'] == 'O' else 'O'
        time.sleep(0.01)
        
    if sock_comunicacao:
        sock_comunicacao.close()
    if sock:
        sock.close()

def thread_servidor_udp(sock, addr):
    global sock_comunicacao, oponente_addr, rodando_jogo, estado_jogo, conectado
    
    with lock_rede:
        estado_jogo['mensagens'].append("Aguardando oponente...")
    sock.bind(addr)
    
    while rodando_jogo and not conectado:
        dados, client_addr = receber_dados(sock, 'udp')
        if dados and dados.get('msg') == 'HELLO':
            with lock_rede:
                oponente_addr = client_addr
                sock_comunicacao = sock
            enviar_dados(sock_comunicacao, {'msg': 'HELLO'}, 'udp', oponente_addr)
            with lock_rede:
                estado_jogo['mensagens'] = ["Oponente conectado!"]
                conectado = True
            break
        time.sleep(0.01)

    while rodando_jogo:
        dados, addr_recebido = receber_dados(sock_comunicacao, 'udp')
        if dados:
            with lock_rede:
                oponente_addr = addr_recebido or oponente_addr
                estado_jogo['tabuleiro'] = dados.get('tabuleiro', estado_jogo['tabuleiro'])
                estado_jogo['turno'] = 'X' if estado_jogo['turno'] == 'O' else 'O'
        time.sleep(0.01)
    
    if sock:
        sock.close()

def thread_cliente_udp(sock, addr):
    global sock_comunicacao, oponente_addr, rodando_jogo, estado_jogo, conectado
    
    host_display = addr[0]
    with lock_rede:
        estado_jogo['mensagens'].append(f"Conectando a {host_display}:{addr[1]}...")
        oponente_addr = addr
        sock_comunicacao = sock

    inicio_tempo = time.time()
    while rodando_jogo and not conectado and (time.time() - inicio_tempo) < 10:
        enviar_dados(sock_comunicacao, {'msg': 'HELLO'}, 'udp', oponente_addr)
        dados, addr_recebido = receber_dados(sock_comunicacao, 'udp')
        if dados and dados.get('msg') == 'HELLO':
            with lock_rede:
                estado_jogo['mensagens'] = ["Conectado ao servidor!"]
                conectado = True
            break
        time.sleep(0.5)
    
    if not conectado:
        with lock_rede:
            estado_jogo['mensagens'].append("Não foi possível conectar ao servidor UDP.")
            rodando_jogo = False
        if sock:
            sock.close()
        return

    while rodando_jogo:
        dados, addr_recebido = receber_dados(sock_comunicacao, 'udp')
        if dados:
            with lock_rede:
                oponente_addr = addr_recebido or oponente_addr
                estado_jogo['tabuleiro'] = dados.get('tabuleiro', estado_jogo['tabuleiro'])
                estado_jogo['turno'] = 'X' if estado_jogo['turno'] == 'O' else 'O'
        time.sleep(0.01)

    if sock:
        sock.close()

# --- Loop principal do menu de configuração ---
def main_menu():
    config = {'protocolo': None, 'modo': None, 'host': '127.0.0.1', 'porta': '5555'}
    estado_menu = 'PROTOCOLO'
    input_ativo = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if estado_menu == 'PROTOCOLO':
                    if desenhar_botao(LARGURA // 2 - 100, 200, 200, 50, VERDE_DESTAQUE, "TCP", FONTE_PADRAO, FUNDO_ESCURO).collidepoint(event.pos):
                        config['protocolo'] = 'tcp'
                        estado_menu = 'MODO'
                    elif desenhar_botao(LARGURA // 2 - 100, 300, 200, 50, VERDE_DESTAQUE, "UDP", FONTE_PADRAO, FUNDO_ESCURO).collidepoint(event.pos):
                        config['protocolo'] = 'udp'
                        estado_menu = 'MODO'
                
                elif estado_menu == 'MODO':
                    if desenhar_botao(LARGURA // 2 - 100, 200, 200, 50, COR_O, "Hospedar", FONTE_PADRAO, BRANCO_CLARO).collidepoint(event.pos):
                        config['modo'] = 'h'
                        estado_menu = 'CONFIG_REDE'
                    elif desenhar_botao(LARGURA // 2 - 100, 300, 200, 50, COR_X, "Conectar", FONTE_PADRAO, BRANCO_CLARO).collidepoint(event.pos):
                        config['modo'] = 'c'
                        estado_menu = 'CONFIG_REDE'
                
                elif estado_menu == 'CONFIG_REDE':
                    if desenhar_caixa_texto(LARGURA // 2 - 150, 250, 300, 50, config['host'], False, FUNDO_ESCURO).collidepoint(event.pos):
                        input_ativo = 'host'
                    elif desenhar_caixa_texto(LARGURA // 2 - 150, 350, 300, 50, config['porta'], False, FUNDO_ESCURO).collidepoint(event.pos):
                        input_ativo = 'porta'
                    else:
                        input_ativo = None
                    
                    if desenhar_botao(LARGURA // 2 - 100, ALTURA - 100, 200, 50, VERDE_DESTAQUE, "Iniciar Jogo", FONTE_PADRAO, FUNDO_ESCURO).collidepoint(event.pos):
                        if config['host'] and config['porta'].isdigit():
                            return config['modo'], config['protocolo'], config['host'], int(config['porta'])

            if event.type == pygame.KEYDOWN and input_ativo:
                if event.key == pygame.K_RETURN:
                    input_ativo = None
                elif event.key == pygame.K_BACKSPACE:
                    if input_ativo == 'host':
                        config['host'] = config['host'][:-1]
                    elif input_ativo == 'porta':
                        config['porta'] = config['porta'][:-1]
                else:
                    if input_ativo == 'host' and len(config['host']) < 39:
                        config['host'] += event.unicode
                    elif input_ativo == 'porta' and len(config['porta']) < 5 and event.unicode.isdigit():
                        config['porta'] += event.unicode

