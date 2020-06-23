default: mfn_api

mfn_api:
	cp -r ../ManagementService/data_layer/ python/
	docker run --rm -it \
                --name mfn_api_generation \
                -e http_proxy=\${http_proxy} \
                -e https_proxy=\${https_proxy} \
                -v $(CURDIR):/root/mfn_api \
                -w /root/mfn_api/python \
		python:3.6 \
                /bin/bash -c 'pip install requests;pip install thrift; pip install pdoc3; pdoc3 --html --output-dir /root/mfn_api/python/doc --force MicroFunctionsAPI.py'
	sed -i 's/<body>/<body bgcolor="#fff">/g' python/doc/MicroFunctionsAPI.html
	mkdir -p ../GUI/app/pages/docs/api/python
	cp python/doc/MicroFunctionsAPI.html ../GUI/app/pages/docs/api/python/
	rm -rf python/data_layer

clean:
	rm -rf python/data_layer
	rm -rf python/doc

