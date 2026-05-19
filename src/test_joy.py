import pygame as pg

pg.init()
pg.joystick.init()

print("Procurando controles...")
joysticks = []
for i in range(pg.joystick.get_count()):
    joy = pg.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    print(f"Controle detectado: {joy.get_name()}")

if not joysticks:
    print("Nenhum controle encontrado! Tente conectar o controle e rodar novamente.")
    pg.quit()
    exit()

print("\nAperte os botões no controle (Pressione ESC no teclado para sair):")
screen = pg.display.set_mode((400, 300))
pg.display.set_caption("Teste de Controle")
font = pg.font.SysFont("consolas", 24)

running = True
while running:
    screen.fill((30, 30, 30))
    for e in pg.event.get():
        if e.type == pg.QUIT:
            running = False
        elif e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
            running = False
        elif e.type == pg.JOYBUTTONDOWN:
            msg = f"Botão pressionado: {e.button}"
            print(msg)
            text = font.render(msg, True, (255, 255, 255))
            screen.blit(text, (20, 130))
        elif e.type == pg.JOYAXISMOTION:
            if abs(e.value) > 0.5:
                msg = f"Eixo movido: {e.axis} (Valor: {e.value:.2f})"
                # Evita flood no terminal
                # print(msg)
                text = font.render(msg, True, (200, 200, 255))
                screen.blit(text, (20, 160))

    pg.display.flip()

pg.quit()
