An example of importing playlists into Rdio, and exporting them out.

This uses the Rdio Python library from:

- https://github.com/rdio/rdio-python

    git clone git@github.com:rdio/rdio-python.git
    cd rdio-python
    python setup.py install

Get your dev oauth app credentials

- http://www.rdio.com/developers/

Write your client.ini that should look like this and live in the root directory of your playlist_helper checkout:

    [oauth]
    client_id=
    client_secret=
    client_callback_uri=https://github.com/jmullan/playlist_helper

You will need to authenticate before you can export your playlists:

    python playlist_helper/authenticate.py

Finally, you can dump your playlist and lists of all of your favorites.

    python playlist_helper/dump.py
