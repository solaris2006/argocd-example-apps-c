import os
import re

eso_template = """
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: vault-secret-example
spec:
  refreshInterval: "15s"
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: vault-secret-example
  data:
  - secretKey: my-vault-injected-password
    remoteRef:
      key: secret/data/guestbook
      property: password
"""

env_from_template = """          envFrom:
            - secretRef:
                name: vault-secret-example
"""

for root, dirs, files in os.walk('/Users/cristians/code/argocd/argocd-example-apps-c'):
    if '.git' in root: continue
    for f in files:
        if f.endswith('deployment.yaml'):
            path = os.path.join(root, f)
            with open(path, 'r') as file:
                content = file.read()
            
            if 'vault-secret-example' in content: continue

            # Append the ESO crd
            content += eso_template
            
            # Inject envFrom after ports or image
            content = re.sub(r'(ports:\n\s+- containerPort: \d+\n)', r'\1' + env_from_template, content)
            
            with open(path, 'w') as file:
                file.write(content)
            
            print(f"Patched {path}")
