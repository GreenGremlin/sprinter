def main(build):
    build.packages.install(".", develop=True)
    build.packages.install("pex")


def test(build):
    main(build)
    build.packages.install("httpretty")
    build.packages.install("mock")
    build.packages.install("nose")
    build.executables.run(
        ["nosetests", "-a", "!full", "--with-coverage", "--cover-package=sprinter"]
    )
