# Samir Ali
# Game3
# CPSC3400
# nickname: theUpended
# heavily inspired by Bungie's Destiny




import json
import re
import sys
import random # for Argos and Riven encounters
import time # immersion
import threading # for riven to reset game

STOP_WORDS = {"a", "an", "the", "in", "on", "with", "to", "from", "at", "using"} # common words that may be used in strings player uses

class TextAdventure:
    def __init__(self, dungeon_file):
        with open(dungeon_file, 'r') as file:
            self.dungeon = json.load(file) # open JSON provided in commandline
        self.current_room = 'entry' # starts in entry room
        self.inventory = [] # initialized an inventory for 'bag' functionality
        self.game_running = True # checks if the game is running
        self.verbs = { # all the verbs in the game
            'go': self.go,
            'take': self.take,
            'open': self.open,
            'use': self.use,
            'look': self.look,
            'attack': self.attack,
            'quit': self.quitGame,
            'bag': self.bag
        }
        self.vault_open = False # checks if all bosses are killed
        self.special_interactions = { # special interactions with killing bosses, or special item interactions
            ('lightblade', 'thedarkblade'): "You draw the LightBlade to face Alak-Hul. The light from the mysterious weapon illuminates the Darkblade, revealing his location.",
            ('orb', 'totem'): "You place the orb into the receptacle at the base of the totem. The glyphs glow in a yellow hue, and shoot a brilliant ray of Light at the Darkblade, staggering him.",
            ('void', 'argos'): "You use the Void Relic on Argos. Cosmic energy swirls around the shield.",
            ('solar', 'argos'): "You use the Solar Relic on Argos. Flames engulf the shield.",
            ('arc', 'argos'): "You use the Arc Relic on Argos. Electricity interweaves with the shield.",
            ('siva', 'argos'): "You use the SIVA Relic on Argos. Nanites infect the shield.",
            ('ice', 'argos'): "You use the Stasis Relic on Argos. Ice crystalizes the shield.",
            ('strand', 'argos'): "You use the Strand Relic on Argos. Life energy infuses with the shield.",
            'thedarkblade': "\033[3mHow... amusing. The Darkblade meets his end, outshone by your brilliance. Even darkness bows to your Light.\033[0m",
            'atheon': "\033[3mAtheon, the Time's Conflux, falls before your power. Time itself yields to your mastery\033[0m",
            'riven': "\033[3mRiven, the Ahamkara, bows before your might. Even the wish dragon cannot resist your intellect.\033[0m",
            'argos': "\033[3mArgos, the Planetary Core, crumbles under your assault. He has been living inside the Leviathan for far too long. I thank you.\033[0m"
        }
        self.conditions = { # conditions used in rooms, specifically SunlessCell, and VaultOfGlass
            'orbUsedOnTotem': False,
            'lightbladeUsedOnDarkblade': False,
            'pastAegisClensed' : False,
            'futureAegisClensed' : False,
            'pastOpen' : False,
            'futureOpen': False
        }
        self.enemyDefeated = { # used for vault check
            'atheon': False,
            'thedarkblade': False,
            'riven': False,
            'argos': False
        }
        self.relics_to_use = [] # used to hold randomized relics for Leviathan encounter
        # riven mechanics
        self.eyesKilled = 0 # checks how many eyes are killed
        self.rivenTimer = 0 # holds timer value


    def removeStopWords(self, player_input):
        words = player_input.lower().split() # converts input to lowercase, and splits it by whitespace
        return ' '.join(word for word in words if word not in STOP_WORDS) # eliminates any stopwords, and rejoins them using .join, and seperating them by whitespace

    def parseInput(self, cleanedInput):
        pattern = r'(\w+)\s?(\w+)?\s?(\w+)?' # any word character, 1 or 0 whitespaces, option of a word character, optional 1 or 0 whitespace, optional word character
        match = re.match(pattern, cleanedInput)
        if match:
            return match.groups()
        return None, None, None

    def go(self, direction, *_):
        if self.current_room == 'VaultOfGlass': # if in the VaultOfGlass, check if the portals are open before moving
            if direction == 'west' and self.conditions['pastOpen'] == True:
                self.current_room = self.dungeon['VaultOfGlass'][direction]
                self.look()
                return
            elif direction == 'east' and self.conditions['futureOpen'] == True:
                self.current_room = self.dungeon['VaultOfGlass'][direction]
                self.look()
                return
            elif direction == 'north':
                self.current_room = self.dungeon['VaultOfGlass'][direction]
                self.look()
                return
            elif direction == 'south': # no south portal directing in the VaultOfGlass
                ()
            else:
                print("You can't go that way. The portal into that timeline has not been opened.")
                return
        if self.current_room == 'entry' and direction == 'vault' and self.vault_open: # if in the start room, and all bosses are killed, go to end the game
            self.current_room = 'Throne'
            print(f"\033[3mThere is beauty to your Light. Let me admire it, up close.\033[0m")
            self.look()
            return
        
        if direction in self.dungeon[self.current_room]: # if the direction exists
            next_room = self.dungeon[self.current_room][direction] # finds the value in the JSON file
            if next_room != "none" and next_room != 'Throne': # backend check for opening the vault.
                self.current_room = next_room # go to the next room
                print(f"You go {direction} and find yourself in the {self.current_room}.")
                if self.current_room == 'Leviathan': # if in the leviathan encounter, randomize 3 relics, and place it into the list
                    self.relics_to_use = random.sample(self.dungeon['Leviathan']['objects'], 3)
                    self.update_argos_description() # update the description of the boss
                self.look()
            else:
                print("You can't go that way.")
        else:
            print("Invalid direction.")

    def take(self, obj, *_):
        obj = obj.lower() # lowercases the object, just in case
        for item in self.dungeon[self.current_room]['objects']: # if the object is in the room
            if item['objID'].lower() == obj and 'TAKE' in item['interactions']: # and object is takable
                self.inventory.append(item) # put object in your inventory
                self.dungeon[self.current_room]['objects'].remove(item) # remove item from room
                print(f"You take the {item['objID']}.")
                return
        print("Can't take this object.")

    def open(self, obj, *_):
        if obj.lower() == 'vault' and self.current_room == 'entry': # if you want to open the vault, and you are in the start room
            if all(self.enemyDefeated.values()): # checks if enemies are all killed in the list
                self.vault_open = True # sets vault to open
                self.dungeon['entry']['objects'][2]['description'] = "The floor beneath you is now ajar, with a darkness that invites you." # changes vault description in room
                print("\033[3mYou are far more entertaining than I anticipated. Meet me. In Person.\033[0m")
            else:
                print("\033[3mYou take me for a fool. We have other guests on aboard, you'll just have to settle the matter of space amongsts youselves. Bah!\033[0m")
        
        # opening the portals, changes the descriptions, depending if you have taken the main relic yet or not.
        elif obj.lower() == 'pastportal' and self.current_room == 'VaultOfGlass':
            self.conditions['pastOpen'] = True
            if len(self.dungeon['VaultOfGlass']['objects']) == 2:
                self.dungeon['VaultOfGlass']['objects'][0]['description'] = "The portal is now active, leading into the past timeline."
            else:
                self.dungeon['VaultOfGlass']['objects'][1]['description'] = "The portal is now active, leading into the past timeline."
            self.look(obj)
        elif obj.lower() == 'futureportal' and self.current_room == 'VaultOfGlass':
            if len(self.dungeon['VaultOfGlass']['objects']) == 2:
                self.dungeon['VaultOfGlass']['objects'][1]['description'] = "The portal is now active, leading into the future timeline."
            else:
                self.dungeon['VaultOfGlass']['objects'][2]['description'] = "The portal is now active, leading into the future timeline."
            self.conditions['futureOpen'] = True
            self.look(obj)
        else:
            for item in self.dungeon[self.current_room]['objects']: # basic open, rarely used
                if item['objID'].lower() == obj and 'OPEN' in item['interactions']: # if open is in verbs possible for object
                    print(f"You open the {obj}.")
                    return
            print("Can't open this object.")

    def use(self, obj1, obj2):
        if obj1.lower() == 'chalice': # if want to end game
            self.finishGame()  # call the method to end the game
            return
        if obj2:
            if obj2.lower() == 'argos':
                if any(relic['objID'].lower() == obj1.lower() for relic in self.relics_to_use) and self.current_room == 'Leviathan':
                    # find the relic in randomized relics that matches object used
                    for relic in self.relics_to_use:
                        if relic['objID'].lower() == obj1.lower():
                            # remove the relic dictionary from randomized relics
                            self.relics_to_use.remove(relic)
                            break  # stop looking for relics
                    # checks if all relics have been used
                    if not self.relics_to_use:
                        # find argos in the current room, and make him vunerable
                        for enemy in self.dungeon[self.current_room].get('enemies', []):
                            if enemy['eneID'].lower() == 'argos':
                                enemy['attackable'] = True
                                print("Argos' shield flickers, and falls due to conflicting energies within it. Argos is now vulnerable.")
                                break  # stop after argos is made vunerbale
                else: # if a relic was not part of the chosen random set, reset encounter
                    print("\nArgos absorbs the attack, and stands unwavered. You are forced to flee from the sheer pressure Argos emits.\n")
                    self.reset_encounter()
                    return
        if obj2: # generic if there is 2 items that is used on eachother
            if (obj1, obj2) in self.special_interactions: # if item interaction is special, print special statement
                print(self.special_interactions[(obj1, obj2)])
                if (obj1, obj2) == ('orb', 'totem'): # if orb-totem mechanic is done, change condition
                    self.conditions['orbUsedOnTotem'] = True
                if (obj1, obj2) == ('lightblade', 'thedarkblade'): # if lightblade-thedarkblade mechanic is done, change condition
                    self.conditions['lightbladeUsedOnDarkblade'] = True
                # if both conditions are met, make theDarkblade vunerable
                if self.conditions['orbUsedOnTotem'] and self.conditions['lightbladeUsedOnDarkblade']:
                    for ene in self.dungeon[self.current_room].get('enemies', []):
                        if ene['eneID'].lower() == "thedarkblade":
                            ene['attackable'] = True
                            print("The Darkblade is now attackable!")
                return
            else: # if nothing happens between the interaction used
                print(f"You use the {obj1} on the {obj2}. Nothing happened.")
        

        if obj1.lower() == 'aegis': # if using the Aegis, alone
            # checks if Aegis is in the inventory
            if any(item['objID'].lower() == 'aegis' for item in self.inventory):
                # update descriptions of relevant objects, showing mechanic was achieved, and changes conditon to make Atheon vunerable
                if self.current_room == 'Past' and not self.conditions['pastAegisClensed']:
                    self.dungeon['Past']['description'] = "The Aegis has cleansed the Past."
                    self.dungeon['Past']['objects'][1]['description'] = "The pressure within the air seems to have dissipated."
                    self.dungeon['Past']['objects'][0]['description'] = "The plants that previously stood still now show life and move freely."
                    self.conditions['pastAegisClensed'] = True
                    self.look()
                elif self.current_room == 'Future' and not self.conditions['futureAegisClensed']:
                    self.dungeon['Future']['description'] = "The Aegis has cleansed the Future"
                    self.dungeon['Future']['objects'][1]['description'] = "The pressure within the air seems to have dissipated."
                    self.conditions['futureAegisClensed'] = True
                    self.look()
                elif self.current_room == 'Future' and self.conditions['futureAegisClensed']: # if already clensed the room
                    print("The Aegis has already cleansed this timeline.")
                elif self.current_room == 'Past' and self.conditions['pastAegisClensed']: # "                          "
                    print("The Aegis has already cleansed this timeline.")

                # make Atheon vulnerable if conditions met
                for enemy in self.dungeon['VaultOfGlass'].get('enemies', []): # Concept implementation was for multiple enemies in VaultOfGlass
                    if enemy['eneID'].lower() == 'atheon':
                        # if conditions met
                        if self.conditions['futureAegisClensed'] and self.conditions['pastAegisClensed']:
                            enemy['attackable'] = True # make atheon attackable
                            print("Atheon's control over the past and present wanes, as Atheon is stuck between timelines. He is vulnerable.")
                            self.dungeon['VaultOfGlass']['enemies'][0]['description'] = "*Atheon* is on one knee, vunerable." # changes description of Atheon
            else:
                print("You don't have the Aegis in your inventory.") # if you don't have the aegis to use it.
            return

        for item in self.inventory:
            if item['objID'].lower() == obj1 and 'USE' in item['interactions']:
                print(f"You use the {obj1} from your inventory.") # classic use item. nothing happens usually.
                return

        if self.current_room in self.special_interactions: # if there is a special interaction with the item if used in the room. was used for easter egg that is not implemented.
            if obj1 in self.special_interactions[self.current_room]:
                print(self.special_interactions[self.current_room][obj1])
                return

        print("Nothing happens.") # default if nothing happens. most statements return to never hit this.

    def update_argos_description(self): # update Argos to display what elements needed to break shield
        argos = next((enemy for enemy in self.dungeon['Leviathan']['enemies'] if enemy['eneID'] == 'Argos'), None) # next() finds the first enemy that has the tag, Argos, and places it into argos value. Was used for concept of 3 enemies in Argos encounter. if nothing is found, which is never, it assigns it to None.
        if argos: # if argos exists
            relic_names = ', '.join([relic['objID'] for relic in self.relics_to_use]) # makes a string, using the relics that weaken Argos' shield, determined when entering the room.
            argos['description'] = f"The Planetary Core stands strong. Use the following relics to weaken him: {relic_names}." # changes argos description. Dynamically changes it due to python semantics
    
    def reset_encounter(self):
    # move the player back to the entry room due to wrong Argos usage
        self.current_room = 'entry'
        # reset any relevant encounter mechanic, such as the relics and Argos' attackable status
        self.relics_to_use = []
        for enemy in self.dungeon[self.current_room].get('enemies', []):
            if enemy['eneID'].lower() == 'argos':
                enemy['attackable'] = False  # reset Argos to not attackable, if initially was
        delay_seconds = 3 # delays just for immersion
        time.sleep(delay_seconds)
        self.look()

    def look(self, obj=None, _=None): # optional object, nonexistant second object
        if obj: # if object exists, look at the object descripton
            obj = obj.lower()
            for item in self.dungeon[self.current_room]['objects']: # for items
                if item['objID'].lower() == obj:
                    print(item['description'])
                    return
            for ene in self.dungeon[self.current_room].get('enemies', []): # for enemies
                if ene['eneID'].lower() == obj:
                    print(ene['description'])
                    return
            print(f"There is no {obj} here.") # f is used to display expressions
        else:
            print(self.dungeon[self.current_room]['description']) # prints room description
            for item in self.dungeon[self.current_room]['objects']: # prints every object description
                print(f"- {item['description']}") 
            for ene in self.dungeon[self.current_room].get('enemies', []):
                print(f"- {ene['description']}")

    def endGameRiven(self): # if riven kills you, end game, else pass
        if not self.enemyDefeated.get('riven', False):
            print("\n\n\033[3mRiven finds you, and you die a gruesome death. Press 'enter' to restart.\033[0m\n")
            self.quitGame()
        else:
            pass


    def attack(self, enemy, weapon): 
        for ene in self.dungeon[self.current_room].get('enemies', []): # if in room currently in
            if ene['eneID'].lower() == enemy:
                if not ene.get('attackable', False): # if attackable
                    print(f"You cannot attack {enemy}.")
                    return
                if weapon not in ene.get('damageable', []): # if damagable
                    print(f"This {weapon} has no effect on {enemy}.")
                    return
                for item in self.inventory: # inventory check, for item used
                    if item['objID'].lower() == weapon:
                        ene['health'] -= 20 # health implementation for concept
                        if ene['health'] <= 0:
                            print(f"You have defeated {enemy} with the {weapon}!")
                            # update the enemies defeated for vault open
                            self.enemyDefeated[enemy] = True
                            # eyes mechanic for Riven
                            if ene['eneID'].lower() == 'eye1':
                                self.eyesKilled += 1
                            if ene['eneID'].lower() == 'eye2':
                                self.eyesKilled += 1
                            if ene['eneID'].lower() == 'eye3':
                                self.eyesKilled += 1
                            # starts timer before the wipe mechanic, and ends game
                            if self.eyesKilled == 3 and self.current_room == 'AscendantRealm':
                                print("Riven screeches, and is on the hunt. She is vunerable in this state.")
                                self.dungeon['AscendantRealm']['enemies'][0]['attackable'] = True
                                self.rivenTimer = threading.Timer(10.0, self.endGameRiven)
                                self.rivenTimer.start()


                            # for specific enemies death, changes descriptions to show success
                            if enemy.lower() == 'atheon':
                                self.dungeon['VaultOfGlass']['description'] = "The Vault of Glass now stands empty, as the body of Atheon now lays lifeless."
                            elif enemy.lower() == 'thedarkblade':
                                self.dungeon['SunlessCell']['description'] = "The Sunless Cell now is met with no darkness, with Alak-Hul's body torn to shreds."
                                self.dungeon['Pit']['objects'][1]['description'] = "the pit's bottom is now visible from above, with the totem in the distance."
                                self.dungeon['Pit']['description'] = "A gaping pit yawns before you, edges etches with runes and glyphs."
    
                            elif enemy.lower() == 'riven':
                                self.dungeon['AscendantRealm']['description'] = "The Ascendant Realm now is eerliy quiet, as the body of the Ahamkara dissipates."
                            elif enemy.lower() == 'argos':
                                self.dungeon['Leviathan']['description'] = "The Underbelly of the Leviathan now lays in silence, with only the machinery making the Leviathan functional, filling the space."
                            # death messages for killing enemies
                            if enemy in self.special_interactions:
                                print(self.special_interactions[enemy])
                            self.dungeon[self.current_room]['enemies'].remove(ene) # remove the enemy from room
                        else:
                            print(f"You attack {enemy} with the {weapon}. {enemy} has {ene['health']} health remaining.") # past implementation of health mechanic
                        return
                print(f"You don't have a {weapon} to attack with.")
                return
        print(f"There is no {enemy} here to attack.")

    def bag(self, *_): # simple inventory mechanic
        if self.inventory:
            print("Inventory:")
            for item in self.inventory:
                print(f"- {item['objID']}")
        else:
            print("Your inventory is empty.")

    def quitGame(self, *_): # if you quit during game
        print("The emperor boasts...")
        print("\033[3mYou fail to complete my challenge. How pitiful. Come back and prove yourself worthy, and I will show you the means to true power.\033[0m")
        self.game_running = False

    def finishGame(self): # if you win the game
        print("\033[3m\nYou take the chalice that Calus offered, and you fall into a deep sleep. As you fade away, you hear Calus in the background, boasting in the distance. 'Goooood! Entertainment that lasts.'\033[0m\n")
        print("You Win! - For now...")
        self.game_running = False


    def play(self): # play state, always running, used to end game
        print("\nWelcome to the Text Adventure!\n")
        print("Available verbs: GO, TAKE, OPEN, USE, LOOK, ATTACK, BAG, QUIT\n")
        print("Tip: Names to interact with items are put in *asterisks* like so. Some items will not have certain interactions.\n")
        print("\n\n\033[3mThis vessel will challenge you in ways you have never dreamed. Let's enjoy ourselves, shall we?\033[0m\n")
        self.look()

        while self.game_running:
            player_input = input("> ") # input for user
            cleanedInput = self.removeStopWords(player_input) # removes stop words
            verb, obj1, obj2 = self.parseInput(cleanedInput) # places input into vars

            if verb in self.verbs:
                self.verbs[verb](obj1, obj2) # if verbs exists
            else:
                print("I don't understand that command.") # if they don't

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python text_adventure.py <dungeon.json>")
    else:
        game = TextAdventure(sys.argv[1])
        game.play()
