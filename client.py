import pygame
import json
import pygame_textinput
""" Overall client structure idea
open pygame window that prompts user to type ip address of the server
After user inputs the address, connect to the server
Then enter the main loop where the users is moving the block around
The user will send their position to the serever 
The server will then broadcast the positions of all clients to each client
and each client will update the positions of the blocks accordingly
"""


pygame.init()

# Create TextInput-object
manager1 = pygame_textinput.TextInputManager(validator=lambda input: len(input) <= 5)
textinput = pygame_textinput.TextInputVisualizer(manager=manager1)

screen = pygame.display.set_mode((1000, 200))
clock = pygame.time.Clock()

while True:
    screen.fill((225, 225, 225))

    events = pygame.event.get()

    # Feed it with events every frame
    textinput.update(events)
    # Blit its surface onto the screen
    screen.blit(textinput.surface, (10, 10))

    for event in events:
        if event.type == pygame.QUIT:
            exit()

    pygame.display.update()
    clock.tick(30)