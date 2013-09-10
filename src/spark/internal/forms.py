
from com.sri.ai.spark.util import SparkForm

#Example : askUser(("First Name", "Last Name"))

def askUser(descriptions):
    form = SparkForm(descriptions)
    form.showForm()
    if form.didUserSubmit():
        print "User clicked on Submit"
        values = tuple(form.getValues())
        print "Values are: ", str(values)
    else:
        print "User clicked on Cancel"
