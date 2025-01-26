<h1>Blockchain Project</h1>
<p>A simple blockchain implementation that uses a PostgreSQL database for persistent storage. The project includes APIs for retrieving the entire blockchain and mining new blocks. The proof-of-work (PoW) algorithm is designed to create hashes containing the last n symbols of the block's timestamp. The blockchain is persistent, stored of a PostgreSQL database. Each time it is loaded, the chain is validated to ensure that it hasn't been tampered with.</p>

<section>
<h2>Features</h2>
<ul>
<li><strong>Blockchain Storage</strong>: All blocks are stored in a PostgreSQL database.</li>
<li><strong>API Endpoints:</strong></li>
<ul>
<li><strong>Get the Blockchain:</strong> Retrieve the entire chain using a GET request at <a href="http://localhost:5000/get_chain">http://localhost:5000/get_chain</a>.</li>
<li><strong>Mine a Block:</strong> Mine a new block using a GET request at <a href="http://localhost:5000/mine">http://localhost:5000/mine</a>.</li>
</ul>
<li><strong>Proof-of-Work:</strong> A block is mined when the PoW algorithm finds a hash that contains the last n symbols of the block's timestamp. n is calculated dynamically.</li></ul>
<h2>Requirements</h2>
<ul>
<li><strong>Python:</strong> Version 3.10 or higher</li>
<li><strong>PostgreSQL:</strong> Ensure PostgreSQL is installed and running.</li>
</ul>