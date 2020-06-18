## Resize Image

### Files

* `resize.py`: function that resizes an image
* `workflow.json`: sample workflow definition file for the resize function
* `request.py`: invoke a deployed workflow containing the resize function with a .jpg file as input
* `test_local.py`: code that locally tests `resize.py`
* `leaves.jpg`: sample image used by `test_local.py`
* `resize.zip`: deployment package (see instructions below)

### Create Deployment package

Python Imaging Library (`pillow`) needs to packaged along with the function code, `resize.py`.

```shell
cd resize

# install pillow alongside user function
docker run -it --rm -e https_proxy=${http_proxy} -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 pip3 install pillow -t .

# create zip package
zip -r ../resize.zip .

cd ..
```

Upload `resize.zip` while creating the `resize` KNIX function.

Use `worflow.json` to create a workflow containing the `resize` function.

### Invoke the workflow with an image

Update `request.py` (`urlstr` variable) with the url of the deployed workflow.

```bash
#invoke workflow with an image
python3 request.py leaves.jpg
```

### Test the function locally

```bash
# install pillow alongside user function
docker run -it --rm -e https_proxy=${http_proxy} -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 pip3 install pillow -t .

# invoke the test script inside a python3.6 docker container
docker run -it --rm -e https_proxy=${http_proxy} -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 python3 test_local.py
```
