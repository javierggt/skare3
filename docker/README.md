SkaRE Docker Images
===================

The only image currently included here can be used to build CentOS 5 ska packages.

I do this to build (although one would normally have the pre-built image registered somewhere):

    docker build -t skare3 .

and I do this to run:

    docker run -v /path/to/my/skare3:/home/ska/skare3-new  -it --rm skare3

Then, to build the conda packages:

    cd skare3-new/
    ./ska_builder.py --tag <tag> <package>

The only "detail" is that the github authentication needs to be handled, so
some commands are missing there.