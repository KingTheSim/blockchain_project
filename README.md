# blockchain_test

This is a testing blockchain, created using Python. It's a direct copy of the one shown here: https://www.geeksforgeeks.org/create-simple-blockchain-using-python/
As of now, the blockchain can be run locally, can mine blocks(http://localhost:5000/mine_block), can view blocks(http://localhost:5000/get_chain) and can show the validity of the chain(http://localhost:5000/valid).
To do any of the shown above, the program must be run in an Pycharm(Probably other IDE's will also work, but I've yet to try it). After the blockchain is run, open any of the links in a browser and the information will displayed.

18.02.2023
Added the ability to store the blocks in a json format file. The code will check if the file exists. If it doesn't, it will create it. If it does exist, it is supposed to use it and to continue the blockchain from the stored information in the file. Currently is broken. Will need to continue working on it later.

19.02.2023
Fixed the blockchain saving and usage. Now, the code will search for a blockchain file. If it exists, it will continue the blockchain from the last block in the file and add any new ones to it.

20.02.2023
Added a resolver to the Blockchain class. It's function is, if the blockchain is found to be invalid, to seek out a valid chain and replace the invalid one. It requires another valid blockchain to work, so it currently doesn't.

21.02.2023
Added a Node class. Also, figured out how to call methods from one class into another and how to create objects that represent the classes outside. Added a method to broadcast the blockchain, to add neighbours. The resolver is moved to the Node class. It wasn't easy to figure out how to use stuff from one class to another, but now it will be more easy.

25.02.2023
I reversed some of the changes that I made, since I am unable to understand them myself.
