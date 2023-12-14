# Installing GPU node and adding it to a KNIX cluster



This is a guide on how to install a GPU node and join it in a running Kubernetes cluster deployed with kubeadm. The guide was tested on a Kubernetes cluster v1.16.6 installed with kubespray, where cluster nodes can be depoyed as VMs using vagrant. VMs in this configuration are running Ubuntu 16.04.4 LTS. 

The node with GPU has a single NVIDIA GTX1050 GPU card.


## Step-by-step guide

1. We start with a blank node with a GPU. This is the node, we would like to join in our Kubernetes cluster. First, update the node and install graphic drivers. The version of the drivers has to be at least 361.93\. We have installed version 450.51.05 and CUDA Version 11.0\. Drivers and CUDA installation is not a part of this guide.

    **NVIDIA drivers information**

```bat
ksatzke@gpuhost:~$ nvidia-smi
Thu Jul 23 10:57:05 2020
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 450.51.05    Driver Version: 450.51.05    CUDA Version: 11.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  GeForce GTX 1050    On   | 00000000:01:00.0  On |                  N/A |
| 30%   46C    P0    N/A /  65W |    604MiB /  1992MiB |      2%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
+-----------------------------------------------------------------------------+
| Processes:                                                                  |
|  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
|        ID   ID                                                   Usage      |
|=============================================================================|
|    0   N/A  N/A      2163      G   /usr/lib/xorg/Xorg                369MiB |
|    0   N/A  N/A      2904      G   /usr/bin/gnome-shell              182MiB |
|    0   N/A  N/A      3000      G   /usr/lib/firefox/firefox            1MiB |
|    0   N/A  N/A      8757      G   /usr/lib/firefox/firefox            1MiB |
|    0   N/A  N/A     11670      C   ...ffice/program/soffice.bin       41MiB |
|    0   N/A  N/A     16245      G   /usr/lib/firefox/firefox            1MiB |
+-----------------------------------------------------------------------------+
```
**CUDA information**

```bat
ksatzke@gpuhost:~$ cat /usr/local/cuda-10.1/version.txt
CUDA Version 10.1.243
``` 

2. The next step is to install Docker on the GPU node. Install Docker CE 19.03 from Docker’s repositories for Ubuntu. Proceed with the following commands as a root user.
```bat
sudo apt-get update
sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
    "deb https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
     $(lsb_release -cs) \
     stable"
sudo apt-get update && sudo apt-get install -y docker-ce=$(apt-cache madison docker-ce | grep 19.03 | head -1 | awk '{print $3}')
```

**Docker installation test**
```bat
ksatzke@gpuhost:~$  docker -–version

Docker version 19.03.11, build 42e35e61f3
```

3.  On the GPU node, add nvidia-docker package repositories, install it and reload Docker daemon configuration, which might be altered by nvidia-docker installation.
    Note that with the release of Docker 19.03, usage of nvidia-docker2 packages are deprecated since NVIDIA GPUs are now natively supported as devices in the Docker runtime.

```bat
# Add the package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

sudo systemctl restart docker
```

**nvidia-docker GPU test**

```bat
ksatzke@gpuhost:~$ docker run --runtime=nvidia --rm nvidia/cuda nvidia-smi
Thu Jul 23 09:17:18 2020
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 450.51.05    Driver Version: 450.51.05    CUDA Version: 11.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  GeForce GTX 1050    On   | 00000000:01:00.0  On |                  N/A |
| 30%   44C    P0    N/A /  65W |    749MiB /  1992MiB |      1%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
+-----------------------------------------------------------------------------+
| Processes:                                                                  |
|  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
|        ID   ID                                                   Usage      |
|=============================================================================|
+-----------------------------------------------------------------------------+
```

4.  Set nvidia-runtime as the default runtime for Docker on the GPU node. Edit the ```bat /etc/docker/daemon.json``` configuration file and set the ```bat default-runtime``` parameter to nvidia. This also allows us to ommit the ```bat  –runtime=nvidia``` parameter for Docker.
```bat
{
        "default-runtime": "nvidia",
        "runtimes": {
            "nvidia": {
                "path": "/usr/bin/nvidia-container-runtime",
                "runtimeArgs": []
            }
        }
    }
```

5.  As a root user on the GPU node, add Kubernetes package repositories and install kubeadm, kubectl and kubelet. Then turn the swap off as it is not supported by Kubernetes.

```bat
apt-get update && apt-get install -y apt-transport-https
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update
apt-get install -y kubelet kubeadm kubectl
# turn off swap or comment the swap line in /etc/fstab
sudo swapoff -a
```
**Specific version installation; e.g., 1.****16****.****6****-00**

```bat
# install aptitude, an interface to package manager 
ksatzke@gpuhost:~$: apt install aptitude -y

# show available kubeadm versions in the repositories
ksatzke@gpuhost:~$ aptitude versions kubeadm
Package kubeadm:                        
p   1.5.7-00    kubernetes-xenial   500 
p   1.6.1-00    kubernetes-xenial   500 
p   1.6.2-00    kubernetes-xenial   500
...
p   1.16.5-00   kubernetes-xenial   500
p   1.16.6-00   kubernetes-xenial   500
...

# install specific version of kubelet, kubeadm and kubectl
ksatzke@gpuhost:~$: apt-get install -y kubelet=1.16.6-00 kubeadm=1.16.6-00 kubectl=1.16.6-00
```

6.  On the GPU node, edit the /etc/systemd/system/kubelet.service.d/10-kubeadm.conf  file and add the following environment argument to enable the DevicePlugins feature gate. If there is already Accelerators feature gate set, remove it.
```bat 
Environment="KUBELET_EXTRA_ARGS=--feature-gates=DevicePlugins=true"
```

**/etc/systemd/system/kubelet.service.d/10-kubeadm.conf**

Note: This drop-in only works with kubeadm and kubelet v1.11+

```bat
[Service]
Environment="KUBELET_KUBECONFIG_ARGS=--bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf -–kubeconfig=/etc/kubernetes/kubelet.conf"

Environment="KUBELET_CONFIG_ARGS=--config=/var/lib/kubelet/config.yaml"
Environment="KUBELET_EXTRA_ARGS=--feature-gates=DevicePlugins=true"

# This is a file that "kubeadm init" and "kubeadm join" generates at runtime, populating the KUBELET_KUBEADM_ARGS variable dynamically

EnvironmentFile=-/var/lib/kubelet/kubeadm-flags.env
# This is a file that the user can use for overrides of the kubelet args as a last resort. Preferably, the user should use
# the .NodeRegistration.KubeletExtraArgs object in the configuration files instead. KUBELET_EXTRA_ARGS should be sourced from this file.

EnvironmentFile=-/etc/default/kubelet
ExecStart=
ExecStart=/usr/local/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_CONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS

```

On the GPU node, reload and restart kubelet to apply previous changes to the configuration.

```bat
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

7.  If not already done, enable GPU support on the Kubernetes master by deploying following Daemonset.

```bat
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.6.0/nvidia-device-plugin.yml
```

8.  For the simplicity, generate a new token on the Kubernetes master and print the join command.

```bat
ksatzke@node1:~$ sudo kubeadm token create --print-join-command

kubeadm join 192.168.1.161:6443 --token gxzpmv.hzqw4q0xxrw8zai7     --discovery-token-ca-cert-hash sha256:696c21540f4de7bd600be843dddc1b362582f4a378547c2cb0d37f3be40d5699
```

9.  Go back to the GPU node and use the printed join command to add GPU node into the cluster.

```bat
ksatzke@gpuhost:~$ sudo kubeadm join 192.168.1.159:6443 --token gxzpmv.hzqw4q0xxrw8zai7     --discovery-token-ca-cert-hash
 sha256:696c21540f4de7bd600be843dddc1b362582f4a378547c2cb0d37f3be40d5699
[preflight] Running pre-flight checks
        [WARNING IsDockerSystemdCheck]: detected "cgroupfs" as the Docker cgroup driver. The recommended driver is "systemd". Please follow the guide at https://kubernetes.io/docs/setup/cri/
        [WARNING SystemVerification]: this Docker version is not on the list of validated versions: 19.03.11. Latest validated version: 18.09
[preflight] Reading configuration from the cluster...
[preflight] FYI: You can look at this config file with 'kubectl -n kube-system get cm kubeadm-config -oyaml'
W0723 13:19:02.377909   27185 defaults.go:199] The recommended value for "clusterDNS" in "KubeletConfiguration" is: [10.233.0.10]; the provided value is: [169.254.25.10]
[kubelet-start] Downloading configuration for the kubelet from the "kubelet-config-1.16" ConfigMap in the kube-system namespace
[kubelet-start] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[kubelet-start] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
[kubelet-start] Activating the kubelet service
[kubelet-start] Waiting for the kubelet to perform the TLS Bootstrap...

This node has joined the cluster:
* Certificate signing request was sent to apiserver and a response was received.
* The Kubelet was informed of the new secure connection details.

Run 'kubectl get nodes' on the control-plane to see this node join the cluster.
```

10.  Run following command on master to see the GPU node (gpuhost) status on the cluster.

```bat
 ksatzke@node1:~$ kubectl get nodes
 
NAME    STATUS     ROLES     AGE       VERSION
gpuhost NotReady   <none>    2m12s     v1.16.6
node1   Ready      master    19h       v1.16.6
node2   Ready      <none>    19h       v1.16.6
node3   Ready      <none>    19h       v1.16.6
node4   Ready      <none>    19h       v1.16.6
```

11.  After a while, the node is ready.

```bat
gpuhost   Ready    <none>    7m        v1.16.6
```

12.  Now we have a GPU node ready in our KNIX Kubernetes cluster. We can label this recently added node (gpuhost) with the "accelerator" type by running following command on the master.

```bat
kubectl label nodes gpuhost accelerator=nvidia-gtx-1050
```

13.  To check nodes for accelerator label, run 
```bat 
kubectl get nodes -L accelerator
``` 
on Kubernetes master.

```bat
ksatzke@gpuhost:~/kubernetes$ kubectl get nodes -L accelerator

NAME      STATUS   ROLES    AGE     VERSION   ACCELERATOR

gpuhost   Ready    <none>   18m     v1.16.6   nvidia-gtx-1050
node1     Ready    master   19h     v1.16.6
node2     Ready    <none>   19h     v1.16.6
node3     Ready    <none>   19h     v1.16.6
node4     Ready    <none>   19h     v1.16.6
```

14.  To test the GPU nodes, go to the master and create a yml file with the following content and execute it.

**gpu-test.yml**

```yaml 
apiVersion: v1
kind: Pod
metadata:
  name: cuda-vector-add
spec:
  restartPolicy: OnFailure
  containers:
  - name: cuda-vector-add
    # https://github.com/kubernetes/kubernetes/blob/v1.7.11/test/images/nvidia-cuda/Dockerfile
    image: "k8s.gcr.io/cuda-vector-add:v0.1"
    resources:
      limits:
        nvidia.com/gpu: 1 # requesting 1 GPU per container
nodeSelector:
  accelerator: nvidia-gtx-1050 # or other nvidia GPU type etc.
```

```bat
ksatzke@node1:~/kubernetes$ kubectl create -f gpu-test.yml
pod "cuda-vector-add" created

ksatzke@node1:~/kubernetes$ kubectl get pods 
NAME                            READY     STATUS      RESTARTS   AGE
cuda-vector-add                 0/1       Completed   0          19s

ksatzke@node1:~/kubernetes$ kubectl logs cuda-vector-add
[Vector addition of 50000 elements]
Copy input data from the host memory to the CUDA device
CUDA kernel launch with 196 blocks of 256 threads
Copy output data from the CUDA device to the host memory
Test PASSED
Done
```
