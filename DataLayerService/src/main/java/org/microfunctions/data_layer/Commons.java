/*
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
package org.microfunctions.data_layer;

public class Commons {
	public static final int LOCAL_DATALAYER = 0;
	
	public static final int RIAK_DATALAYER = 1;
	public static final int WRITE_RIAK_ASYNC_LOCAL_SYNC = -RIAK_DATALAYER;
	public static final int READ_RIAK_ASYNC = -RIAK_DATALAYER;
	public static final int READ_LOCAL_THEN_RIAK = RIAK_DATALAYER + Integer.MIN_VALUE;
}

