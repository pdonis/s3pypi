import os

import boto3
from botocore.exceptions import ClientError

from s3pypi.package import Index, MasterIndex

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


class S3Storage(object):
    """Abstraction for storing package archives and index files in an S3 bucket."""

    def __init__(self, bucket, secret=None, region=None, bare=False, private=False):
        self.s3 = boto3.resource('s3', region_name=region)
        self.bucket = bucket
        self.secret = secret
        self.index = '' if bare else 'index.html'
        self.acl = 'private' if private else 'public-read'

    def _client(self):
        return boto3.client('s3')

    def get_master_index(self):
        try:
            objs = self._client().list_objects(Bucket=self.bucket)
            return MasterIndex(o['Key'].split('/')[0] for o in objs['Contents'] if '/' in o['Key'])
        except ClientError:
            return MasterIndex([])

    def _master_object(self):
        return self.s3.Object(self.bucket, "index.html")

    def put_master_index(self, index):
        self._master_object().put(
            Body=index.to_html(),
            ContentType='text/html',
            CacheControl='public, must-revalidate, proxy-revalidate, max-age=0',
            ACL=self.acl
        )

    def _object(self, package, filename):
        path = '%s/%s' % (package.directory, filename)
        return self.s3.Object(self.bucket, '%s/%s' % (self.secret, path) if self.secret else path)

    def get_index(self, package):
        try:
            html = self._object(package, self.index).get()['Body'].read().decode('utf-8')
            return Index.parse(html)
        except ClientError:
            return Index([])

    def put_index(self, package, index):
        self._object(package, self.index).put(
            Body=index.to_html(),
            ContentType='text/html',
            CacheControl='public, must-revalidate, proxy-revalidate, max-age=0',
            ACL=self.acl
        )

    def put_package(self, package):
        for filename in package.files:
            with open(os.path.join('dist', filename), mode='rb') as f:
                self._object(package, filename).put(
                    Body=f,
                    ContentType='application/x-gzip',
                    ACL=self.acl
                )
