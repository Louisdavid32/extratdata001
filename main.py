from crawl import Crawl
from memory import Memory
from save import Save


def main():
    Crawl(saver=Save(), memory=Memory()).start()


# Lancer le script
if __name__ == "__main__":
    main()
