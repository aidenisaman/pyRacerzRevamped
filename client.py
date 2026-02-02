import pygame
import json
import pygame_textinput
""" Overall client structure idea
open pygame window that prompts user to type ip address of the server
After user inputs the address, swap to the game window and connect to the server
Then enter the main loop where the users is moving the block around
The user will send their position to the server
The server will then broadcast the positions of all clients to each client
and each client will update the positions of the blocks accordingly
"""

def connect_to_server():
    pygame.init()
    ip = ""
    # Create TextInput-object
    manager1 = pygame_textinput.TextInputManager(validator=lambda input: len(input) <= 17)
    textinput = pygame_textinput.TextInputVisualizer(manager=manager1, font_color=(128, 0, 128))

    screen = pygame.display.set_mode((1000, 200))
    pygame.display.set_caption("Enter Server IP Address")
    clock = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))

        events = pygame.event.get()

        # Feed it with events every frame
        textinput.update(events)
        # Blit its surface onto the screen
        screen.blit(textinput.surface, (10, 10))

        for event in events:
            if event.type == pygame.QUIT:
                exit()
            if event.type == pygame.KEYDOWN:
             if event.key == pygame.K_RETURN:
                    ip = textinput.value
                    print(f"IP entered: {ip}:50051")
                    #code to connect to server goes here
                    #After connecting, break out of this loop and enter the main game loop
                    break


        pygame.display.update()
        clock.tick(30)
        if ip != "":
            pygame.quit()
            return ip + ":50051"

def main_game_loop():
    #Main game loop code goes here
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        screen.fill((0, 0, 0))
        pygame.display.update()
        clock.tick(30)

if __name__ == "__main__":
    print(connect_to_server())
    main_game_loop()