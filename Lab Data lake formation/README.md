# Creating and securing a Data Lake

In this AWS lab we are going to create a Data Lake in AWS using Glue for processing and to use a catalog, Lake Formation for permissions, S3 for the underlying data storage, Athena to query the results of the database and finally the datasource to nurish our data lake will be an Aurora database. Here is the overall data arquitecture:

![My Image](Lab%20Data%20lake%20formation/Arquitecture%20schema.png)

# Accessing Aurora

Our first stage will consist of gathering all the information from Aurora, the steps are:

- First we look for the VPC and corresponding the subnets of the Aurora database writer instance, we just need to navigate to the writer instance and copy the VPC and subnets from the "Networking" tab:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20093925.png)

- Once we have that we can look for the Aurora credentials and configurations inside the Secrets Manager:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20094206.png)

- Lastly, we will also gather the information of the lakeformation-users secret:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20094352.png)

# Configuring Lake Formation 

In this second stage we need to configure Lake formation and create a database.  

- The S3 location for the data lake and we supply an IAM that has permissions to read and write inside the S3 bucket, the AWS labs allways provides us with preconfigured IAM roles:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20095125.png)

- Now we will use this registered s3 location to create a the new database using it, the catalog we see is the default catalog and this datase will live inside this particular catalog:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20095906.png)

- Afterwards, we will grant permissions to the previously mentioned IAM role to create tables inside the database and endow it with the hability to give grant this table creating capacity to others inside the "banking_db" database:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20100032.png)
![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20100201.png)

# Glue configuration

With the previous services configured and the data lake intiated, we can now configure the JDBC connector on Glue.

- We use the credential type of username and password and look at the Aurora information of the Secret Manager to fill the username, password and JDBC URL:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20101047.png)

- For the network section that we will find scrolling down, we will use the VPC and sudnet we saw before on the Aurora configuration. The security group we will use in the VPC is the one the lab provides us and tells states what inbound traffic to Aurora is allowed:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20101326.png)
  
- Here we can see all the configuration before creating it:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20101547.png)

# Create the blueprints

Blueprints are a functionality of Lake formation that allows us to create automated, high-level workflows to our data lake. 

- Now we will add a new blueprint of snapshot type which will read the MySQL database refereing the connection we just created on Glue and will then store the tables on the "banking_db" database, selecting the S3 path where the data will be writen too, we also configure it to run on demand:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20101900.png)
![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20102013.png)

- This blueprint will need permissions to read and write to S3 as well as permissions to carry out all the actions that Glue will make under the hood, so we will use again the Glue role provided, we will also set maximum concurrent jobs this blueprint can initiate, and set a table prefix for all tables from MySQL that will be imported to the database "banking_db":

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20102358.png)

- Finally we just have to start it since it runs on demand. If we click on the run_id link we will automatically navigate to the Glue console to see how the workflow is progressing:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20103629.png)

- Once it is run properly every step will be in green:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20104602.png)

- And the process will have generated these resulting tables:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20110302.png)

# Fine-grained permissions

Now we have these tables, let's grant different users specific permissions over the tables:

- Select a table from the datalake and, inside actions, click on "Grant":

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20110446.png)

- We choose the IAM users and roles to be the objects we will grant permissions upon and select a new role which is BusinessAnalysts:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20110539.png)

- And to this IAM role we grant the following permissions, of course they do not have granting permission, they can only make select statements over certain columns if we use column-based access:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20110752.png)

- Now we go out and open a new window on the browser to access AWS, we specify the role we have and the password (again everything provided within the scope of the lab):

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20111335.png)

- Then, inside Athena we can query the table:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20111852.png)

- To conclude, its useful to point out that if we reenter with admin status we have the option to grant permissions to various tables at the same time, we can also see a all the existing roles and the permissions over the tables they have. The "Director" role for instance cannot only make select statements but, on addition it grant this permission to others too:

![My Image](Lab%20Data%20lake%20formation/Captura%20de%20pantalla%202025-06-20%20110446.png)











