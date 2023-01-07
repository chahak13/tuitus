;;; publish.el chahak13.github.io/tuitus -*- lexical-binding: t; -*-

(require 'ox-publish)

(setq org-export-global-macros
      '(("timestamp" . "@@html:<span class=\"timestamp\">[$1]</span>@@")
        ("right-justify" . "@@html:<span class=\"right-justify\">$1</span>@@")))

(defun org-sitemap-custom-entry-format (entry style project)
  "Sitemap PROJECT ENTRY STYLE format that includes date."
  (let ((filename (org-publish-find-title entry project)))
    (if (= (length filename) 0)
        (format "*%s%" entry)
      (format "{{{timestamp(%s)}}} [[file:%s][%s]]"
              (format-time-string "%Y-%m-%d"
                                  (org-publish-find-date entry project))
              entry
              filename))))

;; Enable HTML5
(setq org-html-html5-fancy t
      org-html-doctype "html5")

;; Disable default CSS and JS
(setq org-html-head-include-default-style nil
      org-html-head-include-scripts nil)

(defvar publish-tuitus-css "<link rel=\"stylesheet\" href=\"../style.css\" type=\"text/css\"/>")
(defvar publish-tuitus-header "<div id=\"updated\">Updated: %C</div>
<nav>
<a href=\"/\">Home</a>
<a href=\"/files/sitemap.html\">Posts</a>
</nav>")

(defvar publish-tuitus-footer "<hr/>
<footer>
<div class=\"generated\">
Created with %c
</div>
</footer>
")

(defvar publish-tuitus-base-dir "~/Documents/tuitus/org/")
(defvar publish-tuitus-publish-dir "~/Documents/tuitus/docs/")

;; Render ~verbatim~ as kbd tag in HTML
(add-to-list 'org-html-text-markup-alist '(verbatim . "<kbd>%s</kbd>"))

(setq org-publish-project-alist
      `(("index"
         :base-directory ,publish-tuitus-base-dir
         :base-extension "org"
         :exclude "."
         :include ("index.org")
         :publishing-directory ,publish-tuitus-publish-dir
         :publishing-function org-html-publish-to-html

         :html-head "<link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>"
         :html-preamble "<div id=\"updated\">Updated: %C</div> <nav> <a href=\"/files/sitemap.html\">Posts</a>"
         :html-postamble ,publish-tuitus-footer)

        ("pages"
         :base-directory ,publish-tuitus-base-dir
         :base-extension "org"
         :exclude "index.org"
         :recursive t
         :publishing-directory ,publish-tuitus-publish-dir
         :publishing-function org-html-publish-to-html

         :html-head ,publish-tuitus-css
         :html-preamble ,publish-tuitus-header
         :html-postamble ,publish-tuitus-footer)

        ("blog"
         :base-directory ,(concat publish-tuitus-base-dir "files/")
         :base-extension "org"
         :publishing-directory ,(concat publish-tuitus-publish-dir "files/")
         :publishing-function org-html-publish-to-html

         :auto-sitemap t
         :sitemap-title "Posts"
         :sitemap-filename "sitemap.org"
         :sitemap-sort-files anti-chronologically
         :sitemap-format-entry org-sitemap-custom-entry-format

         :html-head ,publish-tuitus-css
         :html-preamble ,publish-tuitus-header
         :html-postamble ,publish-tuitus-footer)

        ("static"
         :base-directory ,publish-tuitus-base-dir
         :base-extension "css\\|txt\\|jpg\\|gif\\|png"
         :recursive t
         :publishing-directory ,publish-tuitus-publish-dir
         :publishing-function org-publish-attachment)

        ("tuitus" :components ("index" "pages" "blog" "static"))))

(defun publish-tuitus-project ()
  "Publish the entire project and remake index."
  (interactive)
  (org-publish "tuitus")
  (org-publish "index" t))

;; (if (member "t" command-line-args)
;;     (progn
;;       (print "force publish all org files")
;;       (org-publish-all t))
;;     (progn
;;       (print "only publish modified org files")
;;       (org-publish-all)))
(provide 'publish)
;;; publish.el ends here
