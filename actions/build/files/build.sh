#!/bin/sh -l

package=$1
workdir=`pwd`
echo "Building $package"
echo "GIT_USERNAME: ${GIT_USERNAME}"

# If docker user has a different ID than the github user, permissions would not be properly set
#sudo chown -R ska $workdir

cd /home/ska/skare3
./ska_builder.py --tag scm_version --force $package
cd /home/ska/skare3/builds/
mv `find /home/ska/skare3/builds/ -name *tar.bz2` .
files=`ls *tar.bz2`

mv $files $workdir
echo "Built files: $files"
echo ::set-output name=files::$files
