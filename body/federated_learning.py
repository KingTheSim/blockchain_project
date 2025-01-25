# import numpy as np
# import torch
# from PIL import Image


# class FederatedDataset:
#     def __init__(self, data, label, transform=None):
#         self.data = data
#         self.label = label
#         self.transform = transform

#     def __getitem__(self, index=0):
#         data, label = self.data, self.label

#         if self.transform:
#             data = self.transform(data)
#             label = self.transform(label)

#         return data, label
#     # def __init__(self, sentences, labels, transform=None):
#     #     self.sentences = sentences
#     #     self.labels = labels
#     #     self.transform = transform
#     #
#     # def __getitem__(self, index):
#     #     sentence, label = self.sentences[index], self.labels[index]
#     #
#     #     if self.transform:
#     #         sentence = self.transform(sentence)
#     #         label = self.transform(label)
#     #
#     #     return sentence, label
#     #
#     # def __len__(self):
#     #     return len(self.sentences)


# # class FederatedDataLoader:
# #     def __init__(self, hf_dataset, batch_size=1, shuffle=False):
# #         self.dataset = FederatedDataset(hf_dataset[0], hf_dataset[1])
# #         self.batch_size = batch_size
# #         self.shuffle = shuffle
# #
# #     def __iter__(self):
# #         if self.shuffle:
# #             indices = torch.randperm(len(self.dataset))
# #         else:
# #             indices = torch.arange(len(self.dataset))
# #
# #         for start_idx in range(0, len(self.dataset), self.batch_size):
# #             end_idx = min(start_idx + self.batch_size, len(self.dataset))
# #             batch_indices = indices[start_idx:end_idx]
# #             batch = [(x, y) for (x, y) in [self.dataset[i] for i in batch_indices]]
# #             x, y = zip(*batch)
# #             yield torch.stack(x), torch.stack(y)
# #
# #     def __len__(self):
# #         return len(self.dataset)


# def create_model(data_type):
#     if data_type == "text":
#         model = torch.nn.Sequential(
#             torch.nn.Embedding(50000, 32),
#             torch.nn.LSTM(32, 32),
#             torch.nn.Linear(32, 1),
#             torch.nn.Sigmoid()
#         )

#     elif data_type == "image":
#         model = torch.nn.Sequential(
#             torch.nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
#             torch.nn.ReLU(),
#             torch.nn.MaxPool2d(kernel_size=2, stride=2),
#             torch.nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
#             torch.nn.ReLU(),
#             torch.nn.MaxPool2d(kernel_size=2, stride=1),
#             torch.nn.Flatten(),
#             torch.nn.Linear(64 * 16 * 16, 128),
#             torch.nn.ReLU(),
#             torch.nn.Linear(128, 1),
#             torch.nn.Sigmoid()
#         )

#     elif data_type == "video":
#         pass

#     else:
#         raise ValueError("Invalid data type")

#     return model


# def hasher(data):
#     # Text
#     if isinstance(data, str):
#         words = data.split()
#         hashed_words = [hash(word) % 50000 for word in words]
#         tensor_value = torch.tensor(hashed_words, dtype=torch.float32)

#     # Image
#     elif isinstance(data, Image.Image):
#         image_array = np.array(data).flatten() / 255.0
#         tensor_value = torch.tensor(image_array, dtype=torch.float32)

#     # Video
#     elif isinstance(data, list) and isinstance(data[0], Image.Image):
#         video_array = np.stack([np.array(frame).flatten() / 255.0 for frame in data], axis=0)
#         tensor_value = torch.tensor(video_array, dtype=torch.float32)

#     else:
#         raise ValueError("Invalid data type")

#     return tensor_value




# def train_model(model, federated_dataset):
#     # Define model
#     loss_fn = torch.nn.BCELoss()
#     optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

#     # Train model
#     num_epochs = 10  # Can be changed later on. For now, it's hard-coded
#     for epoch in range(num_epochs):
#         x, y = federated_dataset[0], federated_dataset[1]
#         x = torch.stack(x).unsqueeze(0)
#         y = torch.stack(y).unsqueeze(0)

#         y_predict = model(x)
#         loss = loss_fn(y_predict, y)
#         optimizer.zero_grad()
#         loss.backward()
#         optimizer.step()
#         # for x, y in federated_dataloader:
#         #     y_predict = model(x)
#         #     loss = loss_fn(y_predict, y)
#         #     optimizer.zero_grad()
#         #     loss.backward()
#         #     optimizer.step()
#     return model.state_dict()
