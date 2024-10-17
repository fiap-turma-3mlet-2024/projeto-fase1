db = db.getSiblingDB('vitibrasil');
db.createCollection('defaultCollection');
db.defaultCollection.insertOne({});