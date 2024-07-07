import os
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Initialize the tokenizer and model


def rerank_documents(question, documents, metadatas, storage_path):
    """
    Reranks a list of documents and their metadata based on their relevance to a given question.
    
    Parameters:
    question (str): The question to rank documents against.
    documents (list of str): The list of documents to be ranked.
    metadatas (list of dict): The list of metadata corresponding to each document.
    
    Returns:
    list of tuples: A list of tuples where each tuple contains a document, its metadata, and its score,
                    sorted by the score in descending order.
    """

    # os.environ["TRANSFORMERS_CACHE"] = os.path.join(storage_path, "cache")

    # Prepare the pairs for the model
    pairs = [[question, doc] for doc in documents]

    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-reranker-large')
    model = AutoModelForSequenceClassification.from_pretrained('BAAI/bge-reranker-large')
    model.eval()
    
    # Tokenize the inputs
    with torch.no_grad():
        inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
        scores = model(**inputs, return_dict=True).logits.view(-1, ).float()
    
    # Combine documents, their metadata, and their scores
    scored_documents = list(zip(documents, metadatas, scores.tolist()))
    
    # Sort the documents by score in descending order
    ranked_documents = sorted(scored_documents, key=lambda x: x[2], reverse=True)

    combined_results = []
    for doc, metadata, score in ranked_documents:
        combined_results.append({
            "doc": doc,
            "metadata": metadata,
            # "combined_text": doc
            "score": score
        })
    
    return combined_results


# Example usage
result = {
    "documents": [["Hi", "The giant panda (Ailuropoda melanoleuca), sometimes called a panda bear or simply panda, is a bear species endemic to China."]],
    "metadatas": [[{"url": "http://example.com/hi"}, {"url": "http://example.com/panda"}]]
}

# query_text = "What is a panda?"
# documents = result["documents"][0]
# metadatas = result["metadatas"][0]

# ranked_results = rerank_documents(query_text, documents, metadatas)
# for doc, meta, score in ranked_results:
#     print(f"URL: {meta['url']}\nDocument: {doc}\nScore: {score}\n")
