#!/bin/bash
#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

if [ "$RIAK_FLAVOR" == "TS" ]; then
  # Create TS buckets
  echo "Looking for CREATE TABLE schemas in $SCHEMAS_DIR..."
  for f in $(find $SCHEMAS_DIR -name *.sql -print); do
    BUCKET_NAME=$(basename -s .sql $f)
    BUCKET_DEF=$(cat $f)
    $RIAK_ADMIN bucket-type create $BUCKET_NAME '{"props":{"table_def":"'$BUCKET_DEF'"}}'
    $RIAK_ADMIN bucket-type activate $BUCKET_NAME
  done
fi
