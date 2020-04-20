<!--
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
-->
# KNIX MicroFunctions Use Cases

## QR Code Generator Use Case

In this example we will create a function that uses a Python library to encode a text string, such as a URL, as a QR code. We will store the QR code image in the KNIX MicroFunctions object store and also return it as the function output. The Python function code is shown below. The function makes use of two Python libraries named `qrcode` and `pillow` respectively which need to specified as a requirement to the function in the 'Requirements tab of the code editor. All libraries listed in the 'Requirements' tab will be 'pip installed' when the corresponding function is deployed as part of a workflow or during a test execution.

```
#!/usr/bin/python
import qrcode
import base64
import json
from io import BytesIO
from PIL import Image

def handle(event, context):

    # Check if function input JSON contains targetURL field
    if 'targetURL' not in event:
        raise ValueError("No 'targetURL' field in JSON input data")

    # Create QR code for target URL
    img = qrcode.make(event['targetURL'])

    # Save qrcode output as JPG image
    buffered = BytesIO()
    img.save(buffered, format="JPEG")

    # base64-encode img data
    qr_b64 = base64.b64encode(buffered.getvalue()).decode()

    # Store img in MicroFunctions object store
    context.put('qrcode.jpg', qr_b64)

    # Log status
    context.log("Saved QR code image as qrcode.jpg to object store")

    # Return HTML snippet with img data encoded inline
    return "<img src='data:image/jpeg;base64," + qr_b64 + "';>"
```

Our function expects a JSON object as input that contains a field 'targetURL' which specifies the target of the QR code to be generated. The function throws a ValueError exception if the field is not present. Here is an example JSON function input:

```
{ "targetURL" : "http://microfunctions.org" }
```

which generates the QR code below. The QR code image is saved to the object store under the name 'qrcode.jpg'. Please note that the image data needs to be base64-encoded since the `context.put(key, value)` method expects `key` and `value` parameters to be Python strings. It can be downloaded from there by navigating to the 'Object Store' in the web GUI. The `context.log(logEntry)` call writes a line to the function execution log that can be viewed in the function/workflow execution dialog. The output of Python `print` statements and error log entries also show up in the same execution log. Our example function returns the image data along with an HTML snippet which allows the image to be viewed directly in the function/workflow execution dialog of the web GUI by selecting 'HTML' in the 'Execution Output' tab.

![QR Code](app/pages/docs/usecases/qrcode.jpg "QR code for 'http://microfunctions.org'")


<a href="?importWorkflow=qrgen.zip#/workflows" class="btn btn-primary">
    Import QR Generator Workflow Code
</a>

## Parallelized Language Translation

In this use case we make use of Amazon's Translate cloud service to simultaneously translate an English text, supplied as input to the workflow, into three target languages: French, Italian, and German. Subsequently, the translations are sent to Amazon's Polly Text2Speech engine and the resulting MP3 audio files are stored in our KNIX MicroFunctions object store from where they can be downloaded and played.

The image below visualizes the workflow for this use case.

![Parallelized Translation Workflow](app/pages/docs/usecases/parallelTranslationWorkflowVisualization.png)

Shown below is the corresponding Amazon States Language (ASL) specification for this workflow:

```
{
    "Comment": "Parallelized Language Translation",
    "StartAt": "ParallelTranslator",
    "States": {
        "ParallelTranslator": {
            "Type": "Parallel",
            "Next": "CollectResults",
            "Branches": [
                {
                    "StartAt": "Italian",
                    "States": {
                        "Italian": {
                            "Type": "Pass",
                            "Result": {
                                "TargetLanguageCode": "it",
                                "VoiceId": "Carla"
                            },
                            "ResultPath": "$.TargetLanguage",
                            "Next": "TranslateToItalian"
                        },
                        "TranslateToItalian": {"Type": "Task", "Resource": "translate", "Next": "TextToSpeechItalian"},
                        "TextToSpeechItalian": {"Type": "Task", "Resource": "tts", "End": true}

                    }
                },
                {
                    "StartAt": "French",
                    "States": {
                        "French": {
                            "Type": "Pass",
                            "Result": {
                                "TargetLanguageCode": "fr",
                                "VoiceId": "Celine"
                            },
                            "ResultPath": "$.TargetLanguage",
                            "Next": "TranslateToFrench"
                        },
                        "TranslateToFrench": {"Type": "Task", "Resource": "translate", "Next": "TextToSpeechFrench"},
                        "TextToSpeechFrench": {"Type": "Task", "Resource": "tts", "End": true}

                    }
                },
                {
                    "StartAt": "German",
                    "States": {
                        "German": {
                            "Type": "Pass",
                            "Result": {
                                "TargetLanguageCode": "de",
                                "VoiceId": "Marlene"
                            },
                            "ResultPath": "$.TargetLanguage",
                            "Next": "TranslateToGerman"
                        },
                        "TranslateToGerman": {"Type": "Task", "Resource": "translate", "Next": "TextToSpeechGerman"},
                        "TextToSpeechGerman": {"Type": "Task", "Resource": "tts", "End": true}
                    }
                }

            ]
        },
        "CollectResults": {
            "Type": "Task",
            "Resource": "postprocess",
            "End": true
        }
    }
}
```

The workflow consists of three functions, 'translate', 'tts', and 'postprocess'.

The workflow definition invokes up to three instances of the 'translate' function and passes a different language code and voice id parameter value to each instance via the ASL 'Pass' state and 'ResultPath' construct. All instances receive the source text that is to be translated. The 'translate' function code is shown below.

```
#!/usr/bin/python

import boto3

def handle(event, context):

    source_text = event['SourceText']
    target_language_code = event['TargetLanguage']['TargetLanguageCode']
    target_language_voice_id  = event['TargetLanguage']['VoiceId']
    access_key = event['AWSCredentials']['AccessKey']
    secret_key = event['AWSCredentials']['SecretKey']

    # Call AWS Language Translation service to translate source text
    translate_client = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1').client('translate')

    result = translate_client.translate_text(Text=source_text,
            SourceLanguageCode="en", TargetLanguageCode=target_language_code)

    # Create return value JSON object
    return_json = {}
    return_json['SourceText'] = event['SourceText']
    return_json['AWSCredentials'] = {}
    return_json['AWSCredentials']['AccessKey'] = access_key
    return_json['AWSCredentials']['SecretKey'] = secret_key
    return_json['TranslatedText'] = result.get('TranslatedText')
    return_json['TargetLanguageCode'] = target_language_code + "-" + target_language_code.upper()
    return_json['VoiceId'] = target_language_voice_id

    return return_json
```

The 'tts' function shown below is invoked by the 'translate' function and sends the translation result to Amazon's text-to-speech service, called 'Polly'. It then saves the returned mp3 audio data to the KNIX MicroFunctions object store.

```
#!/usr/bin/python
import boto3
import base64
import os
import json

def handle(event, context):

    source_text = event['SourceText']
    translated_text = event['TranslatedText']
    target_language_code = event['TargetLanguageCode']
    target_language_voice_id  = event['VoiceId']
    access_key = event['AWSCredentials']['AccessKey']
    secret_key = event['AWSCredentials']['SecretKey']

    polly_client = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1').client('polly')

    response = polly_client.synthesize_speech(VoiceId=target_language_voice_id,
                    OutputFormat='mp3', LanguageCode=target_language_code,
                    Text = translated_text)

    context.put(target_language_code + ".mp3", base64.b64encode(response['AudioStream'].read()).decode("utf-8"))

    return_json = { "Translation" : translated_text }
    return return_json
```

The 'postprocess' function shown below waits for all instances to finish, collects the translation results, and sends the workflow response to the user. The response contains both the translations as well as the text-to-speech audio which is sent inline as part of an HTML5 audio control.

```
#!/usr/bin/python
import json
import re

def handle(event, context):

    return_str = ""

    if ("Translation" in event[0]):
        italian_tts = context.get("it-IT.mp3")
        italian_tr = re.sub(r"\\u([0-9a-fA-F]{4})", r"&#x\1;", json.dumps(event[0]['Translation']).strip('"'))
        return_str += "<p> <b>Italian:</b> " + italian_tr + "<br><br><audio controls><source src='data:audio/mp3;base64," + italian_tts + "' type='audio/mp3'></audio>"

    if ("Translation" in event[1]):
        french_tts = context.get("fr-FR.mp3")
        french_tr = re.sub(r"\\u([0-9a-fA-F]{4})", r"&#x\1;", json.dumps(event[1]['Translation']).strip('"'))
        return_str += "<p> <b>French:</b> " + french_tr + "<br><br><audio controls><source src='data:audio/mp3;base64," + french_tts + "' type='audio/mp3'></audio>"

    if ("Translation" in event[2]):
        german_tts = context.get("de-DE.mp3")
        german_tr = re.sub(r"\\u([0-9a-fA-F]{4})", r"&#x\1;", json.dumps(event[2]['Translation']).strip('"'))
        return_str += "<p> <b>German:</b> " + german_tr + "<br><br><audio controls><source src='data:audio/mp3;base64," + german_tts + "' type='audio/mp3'></audio>"

    return return_str
```


The workflow expects as input a JSON object containing the translation source text as well as the AWS Credentials to use their services. Here is an example workflow input which produces the output shown below:

```
{
    "SourceText" : "Welcome to MicroFunctions!",
    "AWSCredentials" : { "AccessKey" : "[AWS Access Key]", "SecretKey" : "[AWS Secret Key]" }
}
```

![Parallelized Translation Output](app/pages/docs/usecases/parallelTranslationOutput.png)

<a href="?importWorkflow=parallelizedTranslation.zip#/workflows" class="btn btn-primary">
    Import Parallelized Translation Workflow Code
</a>
