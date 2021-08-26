#!/usr/bin/env python
# coding: utf-8

# In[2]:


from pd3f import extract

text, tables = extract('Liferay.pdf', tables=False, experimental=False, force_gpu=False, lang="multi", fast=False, parsr_location="localhost:3001")


# In[3]:


from pd3f import Export
import json
from collections import Counter
import statistics as stat


# In[19]:


with open('Liferay_parsr.json') as f:
    data = json.load(f)


# In[20]:


def select_paragraph(data):
    para_index = []
    for itr in range(len(data['pages'])):
        element_index = []
        for itr2 in range(len(data['pages'][itr]['elements'])):
            if data['pages'][itr]['elements'][itr2]['type'] == 'paragraph':
                element_index.append(itr2)
        last_el = len(element_index) - 1
        if last_el != -1:
            para_index.append([itr,last_el])
    return para_index 


# In[21]:


def test_repeat_position(data, para_index):
    no_repeats = 5
    hyp_t = []
    hyp_h = []
    status = []
    t_ref = []
    for itr in range(len(para_index)):
        if data['pages'][para_index[itr][0]]['elements'][para_index[itr][1]]['type'] == 'paragraph':
            last_line = len(data['pages'][para_index[itr][0]]['elements'][para_index[itr][1]]['content']) - 1
            if last_line != -1:
                t_dim = data['pages'][para_index[itr][0]]['elements'][para_index[itr][1]]['content'][last_line]['box']['t']
                h_dim = data['pages'][para_index[itr][0]]['elements'][para_index[itr][1]]['content'][last_line]['box']['h']
                hyp_t.append(t_dim)
                hyp_h.append(h_dim)
    counted_el = Counter(hyp_t)
    for key in counted_el:
        if counted_el[key] > 5:
            status.append('true')
            t_ref.append(key)
    status_o = Counter(status)
    if 'true' in status_o.keys():
        status_f = 1 
    else:
        status_f = 0
    h_ref = stat.mode(hyp_h)   
    return t_ref, h_ref, status_f


# In[22]:


def set_margin_limit(data, margin):
    new_exc_margin = []
    for itr in range(len(data['pages'])):
        data['pages'][itr]['margins']['bottom'] = margin
        for itr2 in range(len(data['pages'][itr]['elements'])):
            if data['pages'][itr]['elements'][itr2]['type'] == 'paragraph':
                for itr3 in range(len(data['pages'][itr]['elements'][itr2]['content'])):
                    if data['pages'][itr]['elements'][itr2]['content'][itr3]['box']['t'] > margin:
                        new_exc_margin.append([itr,itr2,itr3])
    return new_exc_margin


# In[23]:


def set_new_footer(data, nf):
    for i in range(len(nf)):
        for j in range(len(data['pages'][nf[i][0]]['elements'][nf[i][1]]['content'][nf[i][2]]['content'])):
            word_el = data['pages'][nf[i][0]]['elements'][nf[i][1]]['content'][nf[i][2]]['content'][j]['properties']
            word_el['isFooter'] = 1
    return data


# In[24]:


class Export:
    """Process parsr's JSON output into an internal document represeation. This is the beginning of the pipeline.
    Not all the magic is happing here.
    """

    def __init__(
        self,
        input_json,
        remove_punct_paragraph=True,
        seperate_header_footer=True,
        remove_duplicate_header_footer=True,
        remove_page_number=True,
        remove_header=False,
        remove_footer=False,
        remove_hyphens=True,
        footnotes_last=True,
        ocrd=None,
        lang="multi",
        fast=False,
    ):
        if type(input_json) is str:
            self.input_data = json.loads(Path(input_json).read_text())
        elif type(input_json) is dict:
            self.input_data = input_json
        else:
            raise ValueError("problem with reading input json data")
            
    def export_header_footer(self):
        headers, footers = [], []

        for idx_page, page in enumerate(self.input_data["pages"]):
            header_per_page, footer_per_page = [], []
            
            for element in page["elements"]:
                if (
                    "isHeader" in element["properties"]
                    and element["properties"]["isHeader"]
                ):
                    element['pageNumber'] = page['pageNumber']
                    header_per_page.append(element)
                if element['type'] == 'paragraph':
                    for idx_line, line in enumerate(element['content']):
                        for idx_word, word in enumerate(line['content']):
                            if (
                                "isFooter" in word["properties"]
                                and word["properties"]["isFooter"]
                            ):
                                line['pageNumber'] = page['pageNumber']
                                footer_per_page.append(line)
            headers.append(header_per_page)
            footers.append(footer_per_page)

        return headers, footers
    
    


# In[25]:


def export(self):
        cleaned_header, cleaned_footer, new_footnotes = None, None, None

        if self.seperate_header_footer:
            cleaned_header, cleaned_footer, new_footnotes = self.export_header_footer()

        cleaned_data = []
        for idx_page, page in enumerate(self.input_data["pages"]):
            logger.info(f"export page #{idx_page}")
            for element in page["elements"]:
                if (
                    (self.seperate_header_footer or self.remove_header)
                    and "isHeader" in element["properties"]
                    and element["properties"]["isHeader"]
                ):
                    continue
                    
                if element['type'] == 'paragraph':
                    for idx_line, line in enumerate(element['content']):
                        for idx_word, word in enumerate(line['content']):
                            if (
                                (self.seperate_header_footer or self.remove_footer)
                                and "isFooter" in word["properties"]
                                and word["properties"]["isFooter"]
                            ):
                                continue
                # currently not used
                if element["type"] == "heading":
                    cleaned_data.append(self.export_heading(element))
                if element["type"] == "paragraph":
                    result_para = self.export_paragraph(element, idx_page)
                    result_para and cleaned_data.append(result_para)

            # only append new foofnotes here, most likel get reorced anyhow
            if new_footnotes is not None:
                footer_on_this_page = [
                    x for x in new_footnotes if x.idx_page == idx_page
                ]
                cleaned_data += footer_on_this_page

        if self.remove_page_number:
            cleaned_header = remove_page_number_header_footer(cleaned_header)
            cleaned_footer = remove_page_number_header_footer(cleaned_footer)

        self.doc = DocumentOutput(
            cleaned_data,
            cleaned_header,
            cleaned_footer,
            self.info.order_page,
            self.lang,
        )
        self.footnotes_last and self.doc.reorder_footnotes()

        # only do if footnootes are reordered
        self.footnotes_last and self.remove_hyphens and self.doc.reverse_page_break()


# In[58]:


def bbox_export(pages):
    bbox_idx = []
    for element in pages:
        if element != []:
            bbox_idx.append(element[0]['pageNumber'])
            bbox_idx.append(element[0]['box']['t'])
            bbox_idx.append(element[0]['box']['h'])
            bbox_idx.append(element[0][])
    return bbox_idx    


# In[59]:


#Main function
r = select_paragraph(data)
set_margin, set_h, status = test_repeat_position(data, r)
if status == 1:
    margin  = set_margin[0] - set_h
    new_footer_index = set_margin_limit(data,margin)
    new_data = set_new_footer(data,new_footer_index)
    margin_xy = list(new_data['pages'][0]['margins'].values())
    
else:
    print("No Footer")
    new_data = data

with open('new_Liferay.json','w') as outfile: #fill in the JSON file for writing
    json.dump(new_data,outfile)


# In[60]:


raw_data = Export(new_data)
header, footer = raw_data.export_header_footer()
margin_header = bbox_export(header)
margin_footer = bbox_export(footer)


# In[61]:


with open('margin_header_Liferay.txt','w') as outfile: #fill in the txt file for writing values of the margins
    for n in margin_header:
        outfile.write(str(n) + "\n")
with open('margin_footer_Liferay.txt','w') as outfile: #fill in the txt file for writing values of the margins
    for n in margin_footer:
        outfile.write(str(n) + "\n")


# In[62]:


with open('header_detail.json','w') as outfile: #fill in the JSON file for writing header information
    json.dump(header,outfile)
with open('footer_detail.json','w') as outfile: #fill in the JSON file for writing footer information
    json.dump(footer,outfile)   

