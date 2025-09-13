const { S3Client } = require('@aws-sdk/client-s3');

function createS3Client() {
  const region = process.env.AWS_REGION || 'us-west-2';
  const endpoint = process.env.AWS_S3_ENDPOINT || undefined;
  const forcePathStyle = process.env.S3_FORCE_PATH_STYLE === '1';

  const cfg = { region };
  if (endpoint) {
    cfg.endpoint = endpoint;
  }
  if (forcePathStyle) {
    cfg.forcePathStyle = true;
  }
  return new S3Client(cfg);
}

module.exports = { createS3Client };
