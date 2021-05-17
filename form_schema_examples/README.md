This folder contains example .json schema files which can be passed to reviewer2 using the `--form-schema-json` arg. 
These modify the form that reviewer2 displays on the data page.  

For example, [str_genotypes.json](https://github.com/broadinstitute/reviewer2/blob/main/form_schema_examples/str_genotypes.json)
changes the form from the default:

![image](https://user-images.githubusercontent.com/6240170/118541214-733a4580-b71f-11eb-9348-27c3c94a20ff.png)

to:

![image](https://user-images.githubusercontent.com/6240170/118540459-9adcde00-b71e-11eb-814c-b9063eab1957.png)



For a list of supported icons (beyond thumbs up, thumbs down), see
https://semantic-ui.com/elements/icon.html

---
To use one of these schemas, you can either download the raw json file and pass its local file path via 
```
python3 -m reviewer2 --form-schema-json path/my_schema.json
```
or just pass the url directly via 
```
python3 -m reviewer2 --form-schema-json https://github.com/broadinstitute/reviewer2/blob/main/form_schema_examples/str_genotypes.json
```
