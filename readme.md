# Kdiff

Essentialy a yaml differ, but K8s way.

## Install

```
pip install git+git://github.com/johnmarcou/kdiff
```

## Upgrade

```
pip install git+git://github.com/johnmarcou/kdiff --upgrade
```

## Example
```
# kdiff examples/ns.yaml examples/ns-label.yaml
### Modified Namespace-default ###
 apiVersion: v1
 kind: Namespace
 metadata:
+  labels:
+    mylabel: ok
   name: default
```

## Uninstall
```
pip unsintall kdiff -y 
```
