{{/* vim: set filetype=mustache: */}}

{{/* Microfunctions's management workflow */}}

{{- define "manager.name" -}}
{{- default (printf "%s-manager" .Chart.Name) .Values.manager.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* We truncate at 40 chars because some Kubernetes name fields are limited to this (by the DNS naming spec). */}}
{{- define "manager.fullname" -}}
{{- printf "mgr-%s" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}


{{/* Microfunctions's riak */}}

{{- define "riak.name" -}}
{{- default .Chart.Name .Values.riak.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "riak.fullname" -}}
{{- printf "rk-%s" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{- define "rkConnect.url" }}
{{- $port := index .Values "riak" "ClientPortProtobuf" | toString -}}
{{- range $num, $e := until (.Values.riak.replicas|int) -}}
    {{- printf "rk-%s-%d.rk-%s.%s.svc.cluster.local:%d" $.Release.Name $num $.Release.Name $.Release.Namespace ($.Values.riak.ClientPortProtobuf|int) -}}
    {{- if lt $num  ( sub ($.Values.riak.replicas|int) 1 ) -}}
      {{- printf "," -}}
    {{- end -}}
{{- end -}}
{{- end -}}

{{- define "dlConnect" }}
{{- range $num, $e := until (.Values.datalayer.replicas|int) -}}
    {{- printf "dl-%s-%d.datalayer.%s.svc.cluster.local:%d" $.Release.Name $num $.Release.Namespace ($.Values.datalayer.port|int) -}}
    {{- if lt $num  ( sub ($.Values.datalayer.replicas|int) 1 ) -}}
      {{- printf "," -}}
    {{- end -}}
{{- end -}}
{{- end -}}

{{/* Microfunctions's Nginx */}}

{{- define "nginx.name" -}}
{{- default .Chart.Name .Values.nginx.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "nginx.fullname" -}}
{{- printf "nx-%s" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{- define "nxConnect.url" }}
{{- $rlsname := .Release.Name -}}
{{- $namespace := .Release.Namespace -}}
{{- $port := index .Values "nginx" "httpPort" | toString -}}
    nx-{{$rlsname}}.{{$namespace}}.svc:{{$port}}
{{- end -}}


{{/* Microfunctions's elasticsearch */}}

{{- define "elastic.name" -}}
{{- default .Chart.Name .Values.elastic.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "elastic.fullname" -}}
{{- printf "es-%s" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{- define "esConnect.url" }}
{{- $rlsname := .Release.Name -}}
{{- $namespace := .Release.Namespace -}}
{{- $port := index .Values "elastic" "clientPort" | toString -}}
    es-{{$rlsname}}.{{$namespace}}.svc:{{$port}}
{{- end -}}


{{/* Microfunctions's triggers_frontend */}}

{{- define "triggersFrontend.name" -}}
{{- default .Chart.Name .Values.triggersFrontend.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "triggersFrontend.fullname" -}}
{{- printf "tf-%s" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{- define "tfConnect.url" }}
{{- $rlsname := .Release.Name -}}
{{- $namespace := .Release.Namespace -}}
{{- $port := index .Values "triggersFrontend" "httpPort" | toString -}}
    tf-{{$rlsname}}.{{$namespace}}.svc:{{$port}}
{{- end -}}
