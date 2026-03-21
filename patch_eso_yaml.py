import os
from ruamel.yaml import YAML, YAMLError

# 1. Configuration
# Change this path if your directory structure is different
SEARCH_PATH = '/Users/cristians/code/argocd/argocd-example-apps-c'

# Initialize YAML parser
yaml = YAML()
yaml.preserve_quotes = True
# Standard K8s indentation: 2 spaces for maps, 4 for sequences (lists)
yaml.indent(mapping=2, sequence=4, offset=2)

# The ExternalSecret object to append as a new document (with --- separator)
eso_manifest = {
    'apiVersion': 'external-secrets.io/v1beta1',
    'kind': 'ExternalSecret',
    'metadata': {'name': 'vault-secret-example'},
    'spec': {
        'refreshInterval': '15s',
        'secretStoreRef': {'name': 'vault-backend', 'kind': 'ClusterSecretStore'},
        'target': {'name': 'vault-secret-example'},
        'data': [{
            'secretKey': 'my-vault-injected-password',
            'remoteRef': {'key': 'secret/data/guestbook', 'property': 'password'}
        }]
    }
}

# The envFrom entry to inject into the containers
env_from_entry = {
    'secretRef': {'name': 'vault-secret-example'}
}

print(f"--- Starting Structural YAML Scan in: {SEARCH_PATH} ---")

files_processed = 0
files_patched = 0

for root, dirs, files in os.walk(SEARCH_PATH):
    # Skip hidden git directories
    if '.git' in root: 
        continue
    
    for f in files:
        if f.endswith('deployment.yaml'):
            files_processed += 1
            path = os.path.join(root, f)
            
            try:
                # 1. Load the file (handles multiple docs separated by ---)
                with open(path, 'r') as file:
                    docs = list(yaml.load_all(file))

                # 2. Check if already patched to prevent duplicates
                if any('vault-secret-example' in str(doc) for doc in docs):
                    print(f"[-] Skipping {path}: Already contains 'vault-secret-example'.")
                    continue

                patched_this_file = False
                
                # 3. Iterate through documents to find the Deployment
                for doc in docs:
                    if doc and isinstance(doc, dict) and doc.get('kind') == 'Deployment':
                        try:
                            # Navigate to: spec -> template -> spec -> containers
                            spec = doc.get('spec', {})
                            template = spec.get('template', {})
                            pod_spec = template.get('spec', {})
                            containers = pod_spec.get('containers', [])

                            for container in containers:
                                # Ensure envFrom exists as a list
                                if 'envFrom' not in container or container['envFrom'] is None:
                                    container['envFrom'] = []
                                
                                # Add our entry if it's not already there
                                if env_from_entry not in container['envFrom']:
                                    container['envFrom'].append(env_from_entry)
                                    patched_this_file = True
                        
                        except Exception as e:
                            print(f"    [!] Error navigating structure in {path}: {e}")
                            continue

                # 4. If we modified the Deployment, add the ESO manifest and save
                if patched_this_file:
                    docs.append(eso_manifest)
                    
                    with open(path, 'w') as file:
                        yaml.dump_all(docs, file)
                    
                    print(f"[*] Patched {path} successfully.")
                    files_patched += 1
                else:
                    print(f"[?] No changes made to {path} (No Deployment found or already updated).")

            except YAMLError as e:
                # This handles the Scanner/Parser errors from Helm templates gracefully
                print(f"[!] WARNING: Skipping {path} - Invalid YAML or Helm template syntax.")
                continue
            except Exception as e:
                print(f"[!] Unexpected error on {path}: {type(e).__name__} - {e}")

print(f"\n--- Finished ---")
print(f"Files scanned: {files_processed}")
print(f"Files successfully patched: {files_patched}")