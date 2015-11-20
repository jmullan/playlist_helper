An example of importing playlists into Rdio, and exporting them out.

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
