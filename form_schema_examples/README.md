This folder contains examples of schema files that can be passed to flipbook using the `--form-schema-json` arg.   
They modify the form that flipbook displays on the image page.  

To use one of these schemas, you can download the JSON file, edit it as needed, and pass it to flipbook via: 
```
python3 -m flipbook --form-schema-json path/my_schema.json
```
or directly pass in the url: 
```
python3 -m flipbook --form-schema-json https://github.com/broadinstitute/flipbook/blob/main/form_schema_examples/str_genotypes.json
```

### Schema format:

The schema JSON file should contain a list of dictionaries. Each dictionary represents a question, and can have   
the following keys:

- `type` *(required)*: the value can be `radio` (for multiple-choice input) or `text` (for text input)
- `columnName` *(required)*: the column name in the output TSV file. Responses to this question will be recorded under this column.  
- `inputLabel`: the label to display ahead of this question (defaults to `columnName`). This can be plain text or html.
- `choices`: required if `type` is `radio`. The value should be a list of dictionaries where each dictionary has a `value` and `label` key that represent a choice available to the user. 
   The `label` will be shown in the form, while the `value` will be recorded in the output TSV file if the user selects this choice. The label can be plain text or html.


### Examples:

For example, [str_genotypes.json](https://github.com/broadinstitute/flipbook/blob/main/form_schema_examples/str_genotypes.json)
changes the form from the default:

![image](https://user-images.githubusercontent.com/6240170/118541214-733a4580-b71f-11eb-9348-27c3c94a20ff.png)

to:

![image](https://user-images.githubusercontent.com/6240170/118540459-9adcde00-b71e-11eb-814c-b9063eab1957.png)


The form can be fully customized. For example, [generic.json](https://github.com/broadinstitute/flipbook/blob/main/form_schema_examples/generic.json)
changes the form to:

![image](https://user-images.githubusercontent.com/6240170/118543032-c3b2a280-b721-11eb-8651-258a378e7bbc.png)

For a list of supported icons (other than thumbs up, thumbs down), see
https://semantic-ui.com/elements/icon.html


### Sharing custom schemas:

If you'd like to add your custom schema as an example to this folder, please submit it in a [github issue](https://github.com/broadinstitute/flipbook/issues) or pull request.
