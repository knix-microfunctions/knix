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
package dummy;

import java.util.ArrayList;

import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class SomeClass
{
    private String name;
    private int count;

    public SomeClass(String n, int c)
    {
        this.name = n;
        this.count = c;
    }

    public void doSomething(MicroFunctionsAPI context)
    {
        ArrayList<String> list = new ArrayList<String>();
        for (int i = 0; i < this.count; i++)
        {
            list.add(this.name + "_" + i);
            context.log("counting... " + i + " list item: " + list.get(i));
        }

    }
}

