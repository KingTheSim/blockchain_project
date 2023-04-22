import hashlib
import random
import torch


class FederatedDataset:
    def __init__(self, sentences, labels, transform=None):
        self.sentences = sentences
        self.labels = labels
        self.transform = transform

    def __getitem__(self, index):
        sentence, label = self.sentences[index], self.labels[index]

        if self.transform:
            sentence = self.transform(sentence)
            label = self.transform(label)

        return sentence, label

    def __len__(self):
        return len(self.sentences)


class FederatedDataLoader:
    def __init__(self, hf_dataset, batch_size=1, shuffle=False):
        self.dataset = FederatedDataset(hf_dataset[0], hf_dataset[1])
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __iter__(self):
        if self.shuffle:
            indices = torch.randperm(len(self.dataset))
        else:
            indices = torch.arange(len(self.dataset))

        for start_idx in range(0, len(self.dataset), self.batch_size):
            end_idx = min(start_idx + self.batch_size, len(self.dataset))
            batch_indices = indices[start_idx:end_idx]
            batch = [(x, y) for (x, y) in [self.dataset[i] for i in batch_indices]]
            x, y = zip(*batch)
            yield torch.stack(x), torch.stack(y)

    def __len__(self):
        return len(self.dataset)


def create_model():
    model = torch.nn.Sequential(
        torch.nn.Linear(1, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 1),
        torch.nn.Sigmoid()
    )
    return model


def hasher(text):
    salt = str(random.random()).encode()
    salted_text = salt + text.encode()
    hash_object = hashlib.sha256(salted_text)
    hash_value = int(hash_object.hexdigest(), 16)
    hash_float = float(hash_value) / float(2 ** 32 - 1)
    tensor_value = torch.clamp(torch.tensor([hash_float], dtype=torch.float32), 0, 1)
    return tensor_value


def train_model(model, federated_dataloader):
    # Define model
    loss_fn = torch.nn.BCELoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

    # Train model
    num_epochs = 10  # Can be changed later on. For now, it's hard-coded
    for epoch in range(num_epochs):
        for x, y in federated_dataloader:
            y_predict = model(x)
            loss = loss_fn(y_predict, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    return model.state_dict()
