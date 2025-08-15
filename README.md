# Projetinhomaravilhoso
O projeto trata de uma aplicação de jogo da velha multiplayer, desenvolvida em python com interface gráfica em pygame e comunicação em rede via TCP ou UDP.Permite que dois jogadores joguem remotamente, seja hospedando o jogo ou conectando-se a um servidor.

#Integrantes: 
1. Dávila Gabriela Cassiano de Araujo - 20231054010025; 
2. Ingrid Mannuelle de Melo Pereira – 20231054010001; 
3. Kauani Maria de Aparecidos Santos Ferreira – 20231054010022; 
4. Maria Vitória de Macedo Souza - 20231054010006.

#Como executar:

1. Verifique se o python está instalado;
2. Instale a biblioteca pygame - no terminal digite: pip install pygame;
3. Execute o programa.
#Como jogar:

1. O menu vai aparecer:
2. Escolha o protocolo: TCP OU UDP;
3. Escolha o modo: Hospedar ou Conectar;
4. Configurar o ip (v6 ou v4) e a porta;
5. Aguarde a conexão do outro jogador e tenha um bom jogo.

#Protocolo de camada de aplicação: 
O código implementa um protocolo de camada de aplicação simples para um jogo da velha em rede P2P. Ele envia o estado do tabuleiro em JSON entre os jogadores usando TCP ou UDP, garantindo a sincronização dos turnos, mensagens de status e desconexões, enquanto a interface gráfica exibe o jogo.

