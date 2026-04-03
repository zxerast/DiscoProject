import sys
sys.dont_write_bytecode = True

from game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()