tempi
=====

Add tempo metadata to your music collection using `The Echo Nest
<http://echonest.com>`_.


Installing
----------

First, sign up for an `EchoNest API key
<https://developer.echonest.com>`_, then add it to the top of tempi.py

::

    $ sudo yum -y install python-virtualenv python-eyed3
    $ virtualenv --system-site-packages env
    $ source env/bin/activate
    $ pip install pyechonest

Using
-----

::

    $ python tempi.py <directory of music>

License
-------

.. image:: https://www.gnu.org/graphics/gplv3-127x51.png
   :target: https://www.gnu.org/licenses/gpl.txt

Author
------

`Luke Macken <http://lewk.org>`_
