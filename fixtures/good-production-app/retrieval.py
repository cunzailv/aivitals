def search(vectorstore, query_embedding, tenant_id):
    return vectorstore.similarity_search(query_embedding, filter={"tenant_id": tenant_id}, k=5)
