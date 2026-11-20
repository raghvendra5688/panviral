# Raw UniProt downloads (2026-03-14)

Original file names are kept for provenance. Contents below were read from the FASTA headers; the UniProt
queries that produced them are only known from the file names, so the "apparent" column is an interpretation.

| File | Entries | Apparent content |
|---|---|---|
| `HMPV.fasta` | 1 | Human metapneumovirus fusion glycoprotein F0 (Q6WB98), a screened protein |
| `uniprotkb_accession_P08668_OR_accession_2026_03_14.fasta.gz` | 20 | Hantavirus envelope glycoproteins (GP) of many strains/species; P08668 (Hantaan) was screened |
| `uniprotkb_Nipah_virus_Fusion_glycoprote_2026_03_14.fasta.gz` | 4 | Nipah virus G/F/M and Hendra virus F; Q9IH62 (Nipah G) was screened |
| `uniprotkb_Adenovirus_Fiber_protein_AND_2026_03_14.fasta.gz` | 14 | Human proteins (e.g. CXADR, CD46, ITGB5, CD80/CD86), apparently adenovirus host-interaction partners |
| `uniprotkb_RSV_Fusion_glycoprotein_F_AND_2026_03_14.fasta.gz` | 8 | Human proteins (e.g. EGFR, IGF1R, FURIN, RAB5A/B/C), apparently RSV host-interaction partners |
| `uniprotkb_accession_O15393_OR_accession_2026_03_14.fasta` | 11 | Human proteins (TMPRSS2, FURIN, IFITM1/2/3, CD209, CLEC4M, …), apparently SARS-CoV-2/viral-entry host factors |

None of the host-protein FASTA files were used for the published screen (which contains only the 9 viral proteins
in `../protein_info.csv`); they are kept in case host-factor screening is added later.
