An example of importing playlists into Rdio, and exporting them out.

How to install
--------------

This uses the Rdio Python library from:

- https://github.com/rdio/rdio-python

~~~
git clone git@github.com:rdio/rdio-python.git
cd rdio-python
python setup.py install
~~~

Get your dev oauth app credentials

- http://www.rdio.com/developers/

Write your client.ini that should look like this and live in the root directory of your playlist_helper checkout:

    [oauth]
    client_id=
    client_secret=
    client_callback_uri=https://github.com/jmullan/playlist_helper

You will need to authenticate before you can export your playlists:

    python playlist_helper/authenticate.py

You should see the following text in your command line. Hopefully a browser will also have been opened for you.

    Please enter device code: AAAA7 on https://rdio.com/device

- Copy that code and go to https://www.rdio.com/device/
- Enter the code into the box
- The script should wait for you to do this.

Finally, you can run the main script to dump your playlist and lists of all of your favorites:

    python playlist_helper/dump.py

What does this export?
----------------------

The exact file naming and file structure will vary, but for me, the file structure looks like:

    dumps/jmullan
    ├── comments.json : a computer-readable recording of all the comments I have made
    ├── comments.txt : all the comments I have made, but readable by a person
    ├── favorite_artists.csv : a list of my favorite artists, openable in excel
    │                          if I didn't have any, this would be empty
    ├── favorite_artists.json : a list of my favorite artists, openable by computers
    │                           if I didn't have any, this would have an empty list in it
    ├── favorite_labels.csv : a list of my favorite labels, openable in excel
    ├── favorite_labels.json : a list of my favorite labels, openable by computers
    ├── favorite_stations.csv : a list of my favorite stations, openable by computers
    ├── favorite_stations.json : a list of my favorite stations, openable by computers
    └── playlists
        ├── owned : these are playlists that I own
        │   ├── Cameras.csv : this is a list of songs in the order they were in the playlist
        │   │                 Artist,Album,Title (fields may change!)
        │   ├── Cameras.jspf : this is a computer-readable version of the same playlist
        │   │                  It has more data than the csv file
        │   ├── wedding.csv
        │   └── wedding.jspf
        ├── collab : these are playlists that I have helped on, but I do not own
        │   ├── Together.csv
        │   ├── Together.jspf
        ├── favorites : these are playlists that I only favorited
        │   ├── AfroCarib.csv
        │   └── AfroCarib.jspf
        └── special : these are "playlists" made from things that were not really playlists
            ├── downloaded.csv : these are the files that I have marked for download
            ├── downloaded.jspf
            ├── favorites.csv : these are the tracks I have favorites and the tracks from albums I have favorited
            └── favorites.jspf

... except that I have a lot more playlists than this! Your file structure will look different.

What is a jspf file?

http://www.xspf.org/jspf/

Why not xspf?

I am not a fan of xml (anymore), so I didn't write it yet. It's on the backlog.
