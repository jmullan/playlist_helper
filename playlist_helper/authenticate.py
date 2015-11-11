#!/usr/bin/env python

import logging
import sys

from playlistcreator import PlaylistCreator


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    pc = PlaylistCreator()
    pc.authenticate()

if __name__ == "__main__":
    main()
