# Check all possible clusters, as your .KUBECONFIG may have multiple contexts:
#kubectl config view -o jsonpath='{"Cluster name\tServer\n"}{range .clusters[*]}{.name}{"\t"}{.cluster.server}{"\n"}{end}'

# Select name of cluster you want to interact with from above output:
#export CLUSTER_NAME="cluster.local"
CLUSTER_NAME=$(kubectl config view -o jsonpath="{.clusters[0].name}")

# Point to the API server referring the cluster name
APISERVER=$(kubectl config view -o jsonpath="{.clusters[?(@.name==\"$CLUSTER_NAME\")].cluster.server}")

# Gets the token value a access api/v1/nodes
TOKEN=$(kubectl get secrets -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='default')].data.token}"|base64 --decode)
echo "This is the found api access token:"
echo $TOKEN

#REGISTRY=192.168.8.181:5000

helm install mfn $PWD/microfunctions  --set apiKey=$TOKEN --set persistence.storageClass=manual


helm upgrade mfn $PWD/microfunctions  --set apiKey=$TOKEN --set persistence.storageClass=manual

