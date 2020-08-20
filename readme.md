# Kdiff

## Install

```
git clone https://github.com/johnmarcou/kdiff
pip install -e kdiff
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

## Upgrade
```
cd kdiff
git pull
```
