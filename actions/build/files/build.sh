#!/bin/sh -l

package=$1
workdir=`pwd`
echo "Building $package"
echo "GIT_USERNAME: ${GIT_USERNAME}"

# If docker user has a different ID than the github user, permissions would not be properly set
#sudo chown -R ska $workdir

cd /home/ska/skare3
./ska_builder.py --force $package

cp -fr /home/ska/skare3/builds $workdir
rm $workdir/builds/*/*json*
files=`ls $workdir/builds/builds`

echo "Built files: $files"
echo ::set-output name=files::$files
